from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages


@login_required
def index(request):
    """App Shell principal de la PWA."""
    return render(request, 'core/index.html')


def login_view(request):
    """Vista de inicio de sesión."""
    if request.user.is_authenticated:
        return redirect('index')

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            next_url = request.GET.get('next', '/')
            return redirect(next_url)
        else:
            messages.error(request, 'Usuario o contraseña incorrectos.')
    else:
        form = AuthenticationForm()

    return render(request, 'core/login.html', {'form': form})


def register_view(request):
    """Vista de registro de nuevo usuario."""
    if request.user.is_authenticated:
        return redirect('index')

    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, '¡Cuenta creada exitosamente!')
            return redirect('index')
        else:
            messages.error(request, 'Corrige los errores del formulario.')
    else:
        form = UserCreationForm()

    return render(request, 'core/register.html', {'form': form})


def logout_view(request):
    """Cerrar sesión."""
    logout(request)
    return redirect('login')


def offline_view(request):
    """Página de fallback cuando no hay conexión."""
    return render(request, 'core/offline.html')
