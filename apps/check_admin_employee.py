from django.contrib.auth.models import User
from employee.models import Employee

try:
    admin = User.objects.get(username='admin')
    print('Testing employee_get access:')
    try:
        emp = admin.employee_get
        print(f'Success: {emp}')
        print(f'Employee ID: {emp.id}')
        print(f'Employee Name: {emp.get_full_name()}')
        print('Employee record exists and is accessible!')
    except Exception as e:
        print(f'Error accessing employee_get: {e}')
        
        # Check if employee exists directly
        try:
            emp_direct = Employee.objects.get(employee_user_id=admin)
            print(f'Employee found via direct query: {emp_direct}')
            print(f'Employee ID: {emp_direct.id}')
            print(f'Employee Name: {emp_direct.get_full_name()}')
        except Employee.DoesNotExist:
            print('No Employee record found for admin user')
        except Exception as e2:
            print(f'Error in direct query: {e2}')
            
except User.DoesNotExist:
    print('Admin user not found')
except Exception as e:
    print(f'Unexpected error: {e}')
    import traceback
    traceback.print_exc()