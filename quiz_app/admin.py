from django.contrib import admin

from .models import Question, Quiz


class QuestionInline(admin.TabularInline):
    model = Question
    extra = 0
    fields = ('question_title', 'question_options', 'answer')


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ('title', 'owner', 'created_at', 'updated_at')
    list_filter = ('owner',)
    search_fields = ('title', 'description')
    readonly_fields = ('created_at', 'updated_at')
    inlines = (QuestionInline,)


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('question_title', 'quiz', 'answer')
    list_filter = ('quiz',)
    search_fields = ('question_title',)
