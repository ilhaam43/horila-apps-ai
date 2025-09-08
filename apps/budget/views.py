from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Sum, Q, Count, F
from django.db import models
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from .models import (
    BudgetCategory, BudgetPlan, ExpenseType, Expense,
    ExpenseAttachment, BudgetAlert, FinancialReport
)
from .serializers import (
    BudgetCategorySerializer, BudgetPlanSerializer, BudgetPlanSummarySerializer,
    ExpenseTypeSerializer, ExpenseSerializer, ExpenseCreateSerializer,
    ExpenseAttachmentSerializer, BudgetAlertSerializer, FinancialReportSerializer,
    BudgetDashboardSerializer, ExpenseApprovalSerializer, BudgetAnalyticsSerializer
)
from .filters import BudgetPlanFilter, ExpenseFilter
from .utils import generate_financial_report, send_budget_alert
from .permissions import BudgetPermission


class BudgetCategoryViewSet(viewsets.ModelViewSet):
    queryset = BudgetCategory.objects.filter(is_active=True)
    serializer_class = BudgetCategorySerializer
    permission_classes = [permissions.IsAuthenticated, BudgetPermission]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']


class ExpenseTypeViewSet(viewsets.ModelViewSet):
    queryset = ExpenseType.objects.filter(is_active=True)
    serializer_class = ExpenseTypeSerializer
    permission_classes = [permissions.IsAuthenticated, BudgetPermission]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']


class BudgetPlanViewSet(viewsets.ModelViewSet):
    queryset = BudgetPlan.objects.all()
    serializer_class = BudgetPlanSerializer
    permission_classes = [permissions.IsAuthenticated, BudgetPermission]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = BudgetPlanFilter
    search_fields = ['name', 'description']
    ordering_fields = ['created_at', 'start_date', 'allocated_amount', 'spent_amount']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return BudgetPlanSummarySerializer
        return BudgetPlanSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.select_related('category', 'created_by', 'approved_by')
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve a budget plan"""
        budget_plan = self.get_object()
        if budget_plan.status != 'draft':
            return Response(
                {'error': 'Only draft budgets can be approved'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            approved_by = request.user.employee_get
        except AttributeError:
            return Response(
                {'error': 'User must have an employee profile to approve budget plans'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        budget_plan.status = 'approved'
        budget_plan.approved_by = approved_by
        budget_plan.approved_at = timezone.now()
        budget_plan.save()
        
        return Response({'message': 'Budget plan approved successfully'})
    
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Activate an approved budget plan"""
        budget_plan = self.get_object()
        if budget_plan.status != 'approved':
            return Response(
                {'error': 'Only approved budgets can be activated'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        budget_plan.status = 'active'
        budget_plan.save()
        
        return Response({'message': 'Budget plan activated successfully'})
    
    @action(detail=True, methods=['get'])
    def analytics(self, request, pk=None):
        """Get budget analytics for a specific plan"""
        budget_plan = self.get_object()
        
        # Calculate analytics data
        expenses = budget_plan.expenses.all()
        monthly_data = []
        
        # Generate monthly breakdown
        current_date = budget_plan.start_date
        while current_date <= budget_plan.end_date:
            month_expenses = expenses.filter(
                expense_date__year=current_date.year,
                expense_date__month=current_date.month
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
            
            monthly_data.append({
                'month': current_date.strftime('%Y-%m'),
                'amount': month_expenses
            })
            
            # Move to next month
            if current_date.month == 12:
                current_date = current_date.replace(year=current_date.year + 1, month=1)
            else:
                current_date = current_date.replace(month=current_date.month + 1)
        
        # Category breakdown
        category_breakdown = expenses.values('expense_type__name').annotate(
            total=Sum('amount')
        ).order_by('-total')
        
        analytics_data = {
            'period': f"{budget_plan.start_date} to {budget_plan.end_date}",
            'total_budget': budget_plan.allocated_amount,
            'total_spent': budget_plan.spent_amount,
            'utilization_rate': budget_plan.utilization_percentage,
            'variance': budget_plan.remaining_amount,
            'category_breakdown': list(category_breakdown),
            'trend_data': monthly_data
        }
        
        serializer = BudgetAnalyticsSerializer(analytics_data)
        return Response(serializer.data)


class ExpenseViewSet(viewsets.ModelViewSet):
    queryset = Expense.objects.all()
    serializer_class = ExpenseSerializer
    permission_classes = [permissions.IsAuthenticated, BudgetPermission]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = ExpenseFilter
    search_fields = ['title', 'description', 'vendor_name', 'receipt_number']
    ordering_fields = ['created_at', 'expense_date', 'amount']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return ExpenseCreateSerializer
        elif self.action == 'approve':
            return ExpenseApprovalSerializer
        return ExpenseSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.select_related(
            'budget_plan', 'expense_type', 'requested_by', 'approved_by'
        ).prefetch_related('attachments')
    
    def perform_create(self, serializer):
        expense = serializer.save()
        
        # Update budget plan spent amount
        budget_plan = expense.budget_plan
        budget_plan.spent_amount = budget_plan.expenses.filter(
            status__in=['approved', 'paid']
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        budget_plan.save()
        
        # Check for budget alerts
        self._check_budget_alerts(budget_plan)
    
    def _check_budget_alerts(self, budget_plan):
        """Check and trigger budget alerts if necessary"""
        utilization = budget_plan.utilization_percentage
        
        # Check threshold alerts
        alerts = BudgetAlert.objects.filter(
            budget_plan=budget_plan,
            alert_type='threshold',
            is_active=True,
            is_sent=False,
            threshold_percentage__lte=utilization
        )
        
        for alert in alerts:
            send_budget_alert(alert)
        
        # Check over budget alert
        if budget_plan.is_over_budget:
            over_budget_alert, created = BudgetAlert.objects.get_or_create(
                budget_plan=budget_plan,
                alert_type='overbudget',
                defaults={
                    'message': f'Budget {budget_plan.name} has exceeded its allocated amount.',
                    'is_active': True
                }
            )
            if created or not over_budget_alert.is_sent:
                send_budget_alert(over_budget_alert)
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve an expense"""
        expense = self.get_object()
        if expense.status != 'pending':
            return Response(
                {'error': 'Only pending expenses can be approved'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = self.get_serializer(expense, data={'status': 'approved'}, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        # Update budget plan spent amount
        budget_plan = expense.budget_plan
        budget_plan.spent_amount = budget_plan.expenses.filter(
            status__in=['approved', 'paid']
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        budget_plan.save()
        
        return Response({'message': 'Expense approved successfully'})
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Reject an expense"""
        expense = self.get_object()
        if expense.status != 'pending':
            return Response(
                {'error': 'Only pending expenses can be rejected'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        expense.status = 'rejected'
        expense.save()
        
        return Response({'message': 'Expense rejected successfully'})
    
    @action(detail=True, methods=['post'])
    def mark_paid(self, request, pk=None):
        """Mark an expense as paid"""
        expense = self.get_object()
        if expense.status != 'approved':
            return Response(
                {'error': 'Only approved expenses can be marked as paid'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        expense.status = 'paid'
        expense.paid_at = timezone.now()
        expense.save()
        
        return Response({'message': 'Expense marked as paid successfully'})


class ExpenseAttachmentViewSet(viewsets.ModelViewSet):
    queryset = ExpenseAttachment.objects.all()
    serializer_class = ExpenseAttachmentSerializer
    permission_classes = [permissions.IsAuthenticated, BudgetPermission]
    
    def perform_create(self, serializer):
        try:
            uploaded_by = self.request.user.employee_get
        except AttributeError:
            uploaded_by = None
        
        serializer.save(
            uploaded_by=uploaded_by,
            file_size=self.request.FILES['file'].size,
            filename=self.request.FILES['file'].name
        )


class BudgetAlertViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = BudgetAlert.objects.all()
    serializer_class = BudgetAlertSerializer
    permission_classes = [permissions.IsAuthenticated, BudgetPermission]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['alert_type', 'is_active', 'is_sent']
    ordering = ['-created_at']
    
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Mark alert as read"""
        alert = self.get_object()
        alert.is_sent = True
        alert.sent_at = timezone.now()
        alert.save()
        
        return Response({'message': 'Alert marked as read'})


class FinancialReportViewSet(viewsets.ModelViewSet):
    queryset = FinancialReport.objects.all()
    serializer_class = FinancialReportSerializer
    permission_classes = [permissions.IsAuthenticated, BudgetPermission]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['report_type']
    search_fields = ['name']
    ordering = ['-created_at']
    
    @action(detail=False, methods=['post'])
    def generate(self, request):
        """Generate a new financial report"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Get format from request data
        report_format = request.data.get('format', 'pdf')
        
        # Save report with format in parameters
        report = serializer.save()
        report.parameters = report.parameters or {}
        report.parameters['format'] = report_format
        report.save()
        
        # Generate the actual report file
        try:
            file_path = generate_financial_report(report)
            report.file_path = file_path
            report.save()
            
            return Response({
                'message': 'Report generated successfully',
                'report_id': report.id,
                'file_path': file_path
            })
        except Exception as e:
            return Response(
                {'error': f'Failed to generate report: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """Download a generated report"""
        report = self.get_object()
        if not report.file_path:
            return Response(
                {'error': 'Report file not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Return file download response
        # Implementation depends on your file storage setup
        return Response({'download_url': report.file_path})


class BudgetDashboardViewSet(viewsets.ViewSet):
    """Dashboard view for budget overview"""
    permission_classes = [permissions.IsAuthenticated, BudgetPermission]
    
    @action(detail=False, methods=['get'])
    def budget_plans(self, request):
        """Get filtered budget plans for dashboard"""
        # Get filter parameters
        status = request.GET.get('status')
        category = request.GET.get('category')
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        utilization_status = request.GET.get('utilization_status')
        budget_min = request.GET.get('budget_min')
        budget_max = request.GET.get('budget_max')
        search = request.GET.get('search')
        
        # Start with all budget plans
        queryset = BudgetPlan.objects.all()
        
        # Apply filters
        if status and status != 'all':
            queryset = queryset.filter(status=status)
        
        if category and category != 'all':
            queryset = queryset.filter(category_id=category)
        
        if start_date:
            try:
                start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
                queryset = queryset.filter(start_date__gte=start_date_obj)
            except ValueError:
                pass
        
        if end_date:
            try:
                end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
                queryset = queryset.filter(end_date__lte=end_date_obj)
            except ValueError:
                pass
        
        if utilization_status and utilization_status != 'all':
            if utilization_status == 'over':
                queryset = queryset.filter(spent_amount__gt=F('allocated_amount'))
            elif utilization_status == 'under':
                queryset = queryset.filter(spent_amount__lt=F('allocated_amount'))
            elif utilization_status == 'critical':
                # Critical means utilization > 90%
                queryset = queryset.annotate(
                    utilization_pct=models.Case(
                        models.When(allocated_amount__gt=0, 
                                  then=models.F('spent_amount') * 100.0 / models.F('allocated_amount')),
                        default=0,
                        output_field=models.FloatField()
                    )
                ).filter(utilization_pct__gt=90)
        
        if budget_min:
            try:
                budget_min_val = Decimal(budget_min)
                queryset = queryset.filter(allocated_amount__gte=budget_min_val)
            except (ValueError, TypeError):
                pass
        
        if budget_max:
            try:
                budget_max_val = Decimal(budget_max)
                queryset = queryset.filter(allocated_amount__lte=budget_max_val)
            except (ValueError, TypeError):
                pass
        
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | 
                Q(description__icontains=search)
            )
        
        # Order by creation date
        queryset = queryset.order_by('-created_at')
        
        # Serialize and return
        serializer = BudgetPlanSerializer(queryset, many=True)
        return Response(serializer.data)
    
    def list(self, request):
        """Get dashboard data"""
        # Calculate dashboard metrics
        total_budgets = BudgetPlan.objects.count()
        active_budgets = BudgetPlan.objects.filter(status='active').count()
        
        budget_aggregates = BudgetPlan.objects.filter(status='active').aggregate(
            total_allocated=Sum('allocated_amount'),
            total_spent=Sum('spent_amount'),
            total_remaining=Sum('remaining_amount')
        )
        
        over_budget_count = BudgetPlan.objects.filter(
            status='active',
            spent_amount__gt=F('allocated_amount')
        ).count()
        
        pending_expenses = Expense.objects.filter(status='pending').count()
        
        # Recent expenses
        recent_expenses = Expense.objects.select_related(
            'budget_plan', 'expense_type', 'requested_by'
        ).order_by('-created_at')[:10]
        
        # Budget utilization data
        budget_utilization = BudgetPlan.objects.filter(status='active').values(
            'name', 'allocated_amount', 'spent_amount'
        )
        
        # Monthly spending trend
        monthly_spending = []
        for i in range(12):
            month_start = timezone.now().replace(day=1) - timedelta(days=30*i)
            month_end = month_start.replace(day=28) + timedelta(days=4)
            month_end = month_end - timedelta(days=month_end.day)
            
            month_total = Expense.objects.filter(
                expense_date__range=[month_start, month_end],
                status__in=['approved', 'paid']
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
            
            monthly_spending.append({
                'month': month_start.strftime('%Y-%m'),
                'amount': month_total
            })
        
        dashboard_data = {
            'total_budgets': total_budgets,
            'active_budgets': active_budgets,
            'total_allocated': budget_aggregates['total_allocated'] or Decimal('0'),
            'total_spent': budget_aggregates['total_spent'] or Decimal('0'),
            'total_remaining': budget_aggregates['total_remaining'] or Decimal('0'),
            'over_budget_count': over_budget_count,
            'pending_expenses': pending_expenses,
            'recent_expenses': ExpenseSerializer(recent_expenses, many=True).data,
            'budget_utilization': list(budget_utilization),
            'monthly_spending': monthly_spending
        }
        
        serializer = BudgetDashboardSerializer(dashboard_data)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def monthly_expense_donut(self, request):
        """Get monthly expense data for donut chart - top 10 categories"""
        # Get current month or specified month
        month_param = request.GET.get('month')
        year_param = request.GET.get('year')
        
        if month_param:
            try:
                # Support both 'YYYY-MM' format and separate month/year params
                if '-' in month_param:
                    year_str, month_str = month_param.split('-')
                    target_date = datetime(int(year_str), int(month_str), 1).date()
                elif year_param:
                    target_date = datetime(int(year_param), int(month_param), 1).date()
                else:
                    target_date = timezone.now().date().replace(day=1)
            except (ValueError, TypeError):
                target_date = timezone.now().date().replace(day=1)
        else:
            target_date = timezone.now().date().replace(day=1)
        
        # Calculate month range
        month_start = target_date
        if target_date.month == 12:
            month_end = target_date.replace(year=target_date.year + 1, month=1) - timedelta(days=1)
        else:
            month_end = target_date.replace(month=target_date.month + 1) - timedelta(days=1)
        
        # Get expense data grouped by category for the month
        expense_by_category = Expense.objects.filter(
            expense_date__range=[month_start, month_end],
            status__in=['approved', 'paid']
        ).select_related('budget_plan__category').values(
            'budget_plan__category__name',
            'budget_plan__category__id'
        ).annotate(
            total_amount=Sum('amount'),
            expense_count=Count('id')
        ).order_by('-total_amount')[:10]  # Top 10 categories
        
        # Format data for donut chart
        chart_data = []
        total_expenses = Decimal('0')
        
        for item in expense_by_category:
            amount = item['total_amount'] or Decimal('0')
            total_expenses += amount
            chart_data.append({
                'category_id': item['budget_plan__category__id'],
                'category_name': item['budget_plan__category__name'] or 'Uncategorized',
                'amount': amount,
                'expense_count': item['expense_count'],
                'percentage': 0  # Will be calculated after getting total
            })
        
        # Calculate percentages
        if total_expenses > 0:
            for item in chart_data:
                item['percentage'] = round(float(item['amount'] / total_expenses * 100), 2)
        
        response_data = {
            'month': month_start.strftime('%Y-%m'),
            'month_name': month_start.strftime('%B %Y'),
            'total_expenses': total_expenses,
            'categories': chart_data,
            'chart_type': 'donut'
        }
        
        return Response(response_data)