from django.contrib import admin

from .models import Question, Quiz


class QuestionInline(admin.TabularInline):
	"""Inline admin interface for quiz questions."""
	model = Question
	extra = 0
	show_change_link = True
	fields = (
		'question_title',
		'answer',
		'question_options',
		'created_at',
		'updated_at',
	)
	readonly_fields = ('created_at', 'updated_at')


@admin.register(Quiz)

class QuizAdmin(admin.ModelAdmin):
	"""Admin interface for quizzes."""
	list_display = ('id', 'title', 'owner', 'video_url', 'created_at', 'updated_at')
	search_fields = ('title', 'description', 'video_url', 'owner__username', 'owner__email')
	list_filter = ('created_at', 'updated_at')
	ordering = ('-created_at',)
	inlines = [QuestionInline]


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
	"""Admin interface for questions."""
	list_display = ('id', 'quiz', 'question_title', 'answer', 'created_at', 'updated_at')
	search_fields = ('question_title', 'answer', 'quiz__title')
	list_filter = ('created_at', 'updated_at')
	ordering = ('-created_at',)
