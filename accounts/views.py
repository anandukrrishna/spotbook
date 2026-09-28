from django.http import HttpResponse
from django.shortcuts import render
from django.views import View

from accounts.models import *

# Create your views here.

# -----auth-----

class Login(View):

    def get(self, request):
        return render(request, 'auth/login.html')
    
    def post(self,request):
        username=request.POST.get('username')
        password=request.POST.get('password')
        print(username)
        print(password)
        try:
            obj = LoginTable.objects.get(username=username,password=password)
            request.session['user_id']=obj.id
            print(request.session['user_id'])

            if obj.usertype == 'admin':
                return HttpResponse('''<script>alert('Login Successfull');window.location='/admin_app/AdminHome'</script>''')
            elif obj.usertype == 'user':
                return HttpResponse('''<script>alert('Login Successfull');window.location='/user_app/'</script>''')
            else:
                return HttpResponse('''<script>alert('User Invalid');window.location='/'</script>''')
        except LoginTable.DoesNotExist:
            return HttpResponse('''<script>alert('Invalid Credentials');window.location='/'</script>''')


