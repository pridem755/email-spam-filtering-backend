from rest_framework import serializers
from .models import ContactSubmission

#Serializers for ContactSubmission model
class ContactSubmissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactSubmission
        fields = ['name', 'email', 'message']

    def validate_name(self, value):
        if len(value.strip()) < 2:
            raise serializers.ValidationError("Name must be at least 2 characters.")
        return value.strip()

    def validate_email(self, value):
        return value.strip().lower()

    def validate_message(self, value):
        if len(value.strip()) < 10:
            raise serializers.ValidationError("Message must be at least 10 characters.")
        if len(value.strip()) > 5000:
            raise serializers.ValidationError("Message cannot exceed 5000 characters.")
        return value.strip()

#Serializer for detailed view of ContactSubmission, including read-only fields
class ContactSubmissionDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactSubmission
        fields = '__all__'
        read_only_fields = [
            'spam_score', 'status', 'created_at',
            'ip_address', 'user_agent', 'email_sent'
        ]