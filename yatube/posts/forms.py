from django import forms

from .models import Comment, Post


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ('text', 'group', 'image')
        labels = {
            'text': "Введите текст",
            'group': "Выберите группу",
        }
        help_texts = {
            'text': "Вы обязательно должны заполнить это поле",
        }


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ('text',)
