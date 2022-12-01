from django.core.mail import send_mail
from django.urls import reverse_lazy
from django.views.generic import CreateView, TemplateView

from .forms import CreationForm, UserLoginForm, UserLogoutForm


class SignUp(CreateView):
    form_class = CreationForm
    success_url = reverse_lazy('posts:index')
    template_name = 'users/signup.html'


class Login(CreateView):
    form_class = UserLoginForm
    success_url = reverse_lazy('posts:index')
    template_name = 'users/login.html'


class LogoutView(TemplateView):
    form_class = UserLogoutForm
    success_url = reverse_lazy('posts:index')
    template_name = 'users/logged_out.html'


send_mail(
    'Тема письма',
    'Текст письма.',
    'from@example.com',
    ['to@example.com'],
    fail_silently=False,
)
