from http import HTTPStatus

from django.test import Client, TestCase
from django.urls import reverse

from posts.models import Comment, Group, Post, User


class PostFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create(username='Unknown')
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.user)
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый текст',
        )
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.comment = Comment.objects.create(
            author=cls.user,
            text='Тестовый комментарий',
        )

    def test_create_post(self):
        """Валидная форма создает запись в базе данных."""
        posts_count = Post.objects.count()
        form_data = {'text': 'Новый текст'}
        response = self.authorized_client.post(
            reverse('posts:post_create'), data=form_data, follow=True
        )
        self.assertRedirects(
            response, reverse(
                'posts:profile',
                kwargs={'username': self.user.username}
            )
        )
        self.assertEqual(Post.objects.count(), posts_count + 1)
        self.assertTrue(self.post.text, form_data['text'])
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_post_edit(self):
        """Валидная форма изменяет запись в базе данных."""
        posts_count = Post.objects.count()
        form_data = {'text': 'Новый текст'}
        edited_post = Post.objects.get(id=self.post.id)
        response = self.authorized_client.post(
            reverse('posts:post_edit', args=({self.post.id})),
            data=form_data,
            follow=True,
        )
        self.assertRedirects(
            response, reverse(
                'posts:post_detail',
                kwargs={'post_id': self.post.id}
            )
        )
        self.assertEqual(Post.objects.count(), posts_count)
        self.assertTrue(edited_post.text, form_data['text'])
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_post_edit_not_for_authorized_clien(self):
        """Валидная форма не изменит запись без авторизации."""
        posts_count = Post.objects.count()
        form_data = {'text': 'Новый текст'}
        edited_post = Post.objects.get(id=self.post.id)
        response = self.client.post(
            reverse('posts:post_edit', args=({self.post.id})),
            data=form_data,
            follow=True,
        )
        self.assertRedirects(
            response,
            f'/auth/login/?next=/posts/{self.post.id}/edit/')
        self.assertEqual(Post.objects.count(), posts_count)
        self.assertNotEqual(edited_post.text, form_data['text'])
        self.assertEqual(response.status_code, HTTPStatus.OK)
