import shutil
import tempfile

from django import forms
from django.conf import settings
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..models import Comment, Follow, Group, Post, User

TEMP_NUMB_FIRST_PAGE = 10
POSTS_PER_PAGE = 10


class PostPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='NoName')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
            group=cls.group,
        )
        cls.comment = Comment.objects.create(
            author=cls.user,
            text='Тестовый комментарий',
        )

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(PostPagesTests.user)

    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_pages_names = {
            reverse('posts:index'): 'posts/index.html',
            reverse(
                'posts:group_list', kwargs={'slug': self.group.slug}
            ): 'posts/group_list.html',
            reverse(
                'posts:profile', kwargs={'username': self.post.author}
            ): 'posts/profile.html',
            reverse(
                'posts:post_detail', kwargs={'post_id': self.post.pk}
            ): 'posts/post_detail.html',
            reverse(
                'posts:post_edit', kwargs={'post_id': self.post.pk}
            ): 'posts/create_post.html',
            reverse('posts:post_create'): 'posts/create_post.html',
        }
        for template, reverse_name in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(template)
                self.assertTemplateUsed(response, reverse_name)

    def test_index_show_correct_context(self):
        """Шаблон index сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:index'))
        expected = list(Post.objects.all()[:10])
        self.assertEqual(list(response.context['page_obj']), expected)

    def test_group_list_show_correct_context(self):
        """Шаблон group_list сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse('posts:group_list', kwargs={'slug': self.group.slug})
        )
        expected = list(Post.objects.filter(group_id=self.group.id)[:10])
        self.assertEqual(list(response.context['page_obj']), expected)

    def test_profile_show_correct_context(self):
        """Шаблон profile сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse('posts:profile', args=(self.post.author,))
        )
        expected = list(Post.objects.filter(author_id=self.user.id)[:10])
        self.assertEqual(list(response.context['page_obj']), expected)

    def test_create_edit_show_correct_context(self):
        """Шаблон post_detail сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:index'))
        post_object = response.context['page_obj'][0]
        post_text = post_object.id
        post_user = post_object.author
        post_group = post_object.group
        self.assertEqual(post_text, self.post.pk)
        self.assertEqual(post_user, self.post.author)
        self.assertEqual(post_group, self.post.group)

    def test_create_show_correct_context(self):
        """Шаблон create_edit сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse('posts:post_edit', kwargs={'post_id': self.post.pk})
        )
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.models.ModelChoiceField,
            'image': forms.fields.ImageField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context['form'].fields[value]
                self.assertIsInstance(form_field, expected)

    def test_create_show_correct_context(self):
        """Шаблон create сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:post_create'))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.models.ModelChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context['form'].fields[value]
                self.assertIsInstance(form_field, expected)

    def test_check_post_in_chosen_group_list(self):
        """Проверяем создание поста на страницах с выбранной группой."""
        form_fields = {
            reverse('posts:index'): Post.objects.get(group=self.post.group),
            reverse(
                'posts:group_list', kwargs={'slug': self.group.slug}
            ): Post.objects.get(group=self.post.group),
            reverse(
                'posts:profile', kwargs={'username': self.post.author}
            ): Post.objects.get(group=self.post.group),
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                response = self.authorized_client.get(value)
                form_field = response.context['page_obj']
                self.assertIn(expected, form_field)

    def test_check_post_in_correct_group_list(self):
        """Проверяем чтобы созданный пост был в предназначенной группе."""
        form_fields = {
            reverse(
                'posts:group_list', kwargs={'slug': self.group.slug}
            ): Post.objects.exclude(group=self.post.group),
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                response = self.authorized_client.get(value)
                form_field = response.context['page_obj']
                self.assertNotIn(expected, form_field)

    def test_comment_has_correct_context(self):
        """Kомментарий появляется на странице поста."""
        form_data = {'text': 'Новый комментарий'}
        comment_count = Comment.objects.count()
        response = self.authorized_client.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post.id}),
            data=form_data,
            follow=True,
        )
        self.assertRedirects(
            response, reverse(
                'posts:post_detail',
                kwargs={'post_id': self.post.id}
            )
        )
        self.assertTrue(self.post.text, form_data['text'])
        self.assertEqual(Comment.objects.count(), comment_count + 1)

    def test_check_cache(self):
        """Тестирование кеша."""
        response = self.authorized_client.get(reverse('posts:index'))
        post_1 = response.content
        post_delete = Post.objects.get(id=1)
        response2 = self.authorized_client.get(reverse('posts:index'))
        post_delete.delete()
        post_2 = response2.content
        self.assertEqual(post_1, post_2, 'Ошибка')
        cache.clear()
        post_cache_clear = self.authorized_client.get(reverse('posts:index'))
        self.assertNotEqual(post_1, post_cache_clear, 'Ошибка')


class FollowViewsTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.following = User.objects.create_user(username='following')
        cls.follower = User.objects.create_user(username='follower')
        cls.post = Post.objects.create(
            author=cls.following,
            text='Тестовый текст',
        )

    def setUp(self):
        cache.clear()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.follower)
        self.follower_client = Client()
        self.follower_client.force_login(self.following)

    def test_follow_author_page(self):
        """Тестирование подписки на автора и появление поста."""
        count = Follow.objects.count()
        self.follower_client.get(reverse(
            'posts:profile_follow',
            kwargs={'username': self.follower})
        )
        follow = Follow.objects.all().latest('id')
        self.assertEqual(Follow.objects.count(), count + 1)
        self.assertEqual(follow.author_id, self.follower.id)
        self.assertEqual(follow.user_id, self.following.id)

    def test_unfollow_author_page(self):
        """Тестирование отписки на автора."""
        post = Post.objects.create(
            author=self.following,
            text='Тестовый текст'
        )
        Follow.objects.create(
            user=self.follower,
            author=self.following
        )
        response = self.authorized_client.get(
            reverse('posts:follow_index')
        )
        post_object = response.context['page_obj']
        self.assertIn(post, post_object)

    def test_post_at_unfollow_page(self):
        """Тестирование появления поста у не подписчика."""
        post = Post.objects.create(
            author=self.following,
            text='Тестовый текст'
        )
        response = self.authorized_client.get(
            reverse('posts:follow_index')
        )
        post_object = response.context['page_obj']
        self.assertNotIn(post, post_object)


TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostMediaTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super(PostMediaTests, cls).setUpClass()
        cls.user = User.objects.create_user(username='NoName')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-group-slug',
            description='Тестовое описание группы',
        )
        cls.small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        cls.uploaded = SimpleUploadedFile(
            name='small.gif',
            content=cls.small_gif,
            content_type='image/gif'
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый текст',
            group=cls.group,
            image=cls.uploaded
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.authorized_client = Client()

    def test_image_in_index_page(self):
        """Изображение передаётся на главную страницу."""
        template = reverse('posts:index')
        for url in template:
            response = self.authorized_client.get(url)
            expected = response.context['page_obj'][0]
            self.assertEqual(expected.image, self.post.image)

    def test_image_in_profile_page(self):
        """Изображение передаётся на на страницу профайла."""
        response = self.authorized_client.get(
            reverse('posts:profile', args=(self.post.author,))
        )
        expected = response.context['page_obj'][0]
        self.assertEqual(expected.image, self.post.image)

    def test_image_in_group_page(self):
        """Изображение передаётся на на страницу группы."""
        response = self.authorized_client.get(
            reverse('posts:group_list', kwargs={'slug': self.group.slug}),
        )
        expected = response.context['page_obj'][0]
        self.assertEqual(expected.image, self.post.image)

    def test_image_in_post_detail(self):
        """Изображение передаётся на страницу поста."""
        response = self.authorized_client.get(
            reverse('posts:post_detail', kwargs={'post_id': self.post.id})
        )
        expected = response.context['post']
        self.assertEqual(expected.image, self.post.image)


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.authorized_client = Client()
        cls.author = User.objects.create_user(username='NoName')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание'
        )

    def setUp(self):
        for post_temp in range(TEMP_NUMB_FIRST_PAGE):
            Post.objects.create(
                text=f'text{post_temp}', author=self.author, group=self.group
            )

    def test_first_page_contains_ten_records(self):
        """Проверка: количество постов равно 10."""
        response = self.authorized_client.get(reverse('posts:index'))
        expected = list(Post.objects.all()[:10])
        self.assertEqual(list(response.context['page_obj']), expected)
