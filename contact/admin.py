from django.contrib import admin
from django.utils.html import format_html
from .models import ContactSubmission, TrainingDataset, ModelVersion

#Registering ContactSubmission model with custom admin interface
@admin.register(ContactSubmission)
class ContactSubmissionAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'email', 'spam_score_display',
        'status', 'email_sent', 'created_at'
    ]
    list_filter = ['status', 'email_sent', 'created_at']
    search_fields = ['name', 'email', 'message']
    ordering = ['-created_at']
    readonly_fields = [
        'spam_score', 'ip_address', 'user_agent',
        'created_at', 'email_sent'
    ]
    list_per_page = 25
    actions = ['mark_as_ham', 'mark_as_spam']

    fieldsets = (
        ('Sender Info', {
            'fields': ('name', 'email', 'ip_address', 'user_agent')
        }),
        ('Message', {
            'fields': ('message',)
        }),
        ('ML Scoring', {
            'fields': ('spam_score', 'status', 'email_sent')
        }),
        ('Review', {
            'fields': ('reviewed_by', 'reviewed_at', 'notes')
        }),
    )

    def spam_score_display(self, obj):
        score = obj.spam_score
        if score >= 0.70:
            color = '#ef4444'
            label = f'SPAM ({score:.2f})'
        elif score >= 0.40:
            color = '#f59e0b'
            label = f'UNCERTAIN ({score:.2f})'
        else:
            color = '#10b981'
            label = f'CLEAN ({score:.2f})'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, label
        )
    spam_score_display.short_description = 'Spam Score'

    @admin.action(description='Mark selected as HAM (not spam)')
    def mark_as_ham(self, request, queryset):
        queryset.update(status='accepted', reviewed_by=request.user.username)
        self.message_user(request, f'{queryset.count()} submission(s) marked as ham.')

    @admin.action(description='Mark selected as SPAM')
    def mark_as_spam(self, request, queryset):
        queryset.update(status='spam', reviewed_by=request.user.username)
        self.message_user(request, f'{queryset.count()} submission(s) marked as spam.')

#Registering additional models for training dataset and model versions
@admin.register(TrainingDataset)
class TrainingDatasetAdmin(admin.ModelAdmin):
    list_display = ['label', 'source', 'confidence', 'used_in_training', 'created_at']
    list_filter = ['label', 'source', 'used_in_training']
    search_fields = ['message']
    ordering = ['-created_at']
    list_per_page = 50

#Registering ModelVersion with custom admin interface
@admin.register(ModelVersion)
class ModelVersionAdmin(admin.ModelAdmin):
    list_display = [
        'version', 'accuracy', 'f1_score',
        'precision', 'recall', 'training_samples',
        'is_active', 'created_at'
    ]
    list_filter = ['is_active']
    ordering = ['-created_at']
    readonly_fields = ['created_at']
