from users.forms import CustomUserCreationForm
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from users.forms import CustomAuthenticationForm
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages


def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('login')
    else:
        form = CustomUserCreationForm()

    return render(request, 'users/register.html', {'form': form})



def login_view(request):
    if request.method == 'POST':
        form = CustomAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            # Extract username and password from the cleaned data
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            
            # Authenticate the user
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                # Redirect to the products page after successful login
                return redirect('/products/')
            else:
                # If authentication fails, show an error message
                form.add_error(None, 'Invalid login credentials')
        else:
            # If form is not valid, show a general error message
            messages.error(request, "Please correct the errors below.")
    else:
        form = CustomAuthenticationForm()

    return render(request, 'users/login.html', {'form': form})




# Logout view
def logout_view(request):
    logout(request)
    return render(request, 'users/logout.html')
