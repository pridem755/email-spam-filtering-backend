from django.shortcuts import render
import os
import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework import serializers
from drf_spectacular.utils import extend_schema, inline_serializer, OpenApiExample, OpenApiResponse
from .models import ContactSubmission
from .serializers import ContactSubmissionSerializer
from .ml_engine import score_message
from .email_service import send_contact_email

logger = logging.getLogger(__name__)

# Contact submission API view
class ContactSubmitView(APIView):
    @extend_schema(
        summary='Submit a contact message',
        description=(
            'Validates the message, scores it with the ML spam classifier and stores it. '
            'A message is spam when its score is at or above SPAM_THRESHOLD (default 0.70). '
            'Clean messages are emailed to the site owner; spam is stored but not forwarded. '
            'Clean and spam submissions both return 201, so senders cannot tell if they were flagged.\n\n'
            'Honeypot: an optional `website` field should be left empty. If it is filled in, the API '
            'returns 200 and nothing is stored.'
        ),
        tags=['Contact'],
        request=ContactSubmissionSerializer,
        responses={
            201: OpenApiResponse(
                response=inline_serializer(name='ContactSubmitSuccess', fields={'success': serializers.BooleanField()}),
                description='Submission stored (clean or spam).',
            ),
            200: OpenApiResponse(
                response=inline_serializer(name='ContactSubmitHoneypot', fields={'success': serializers.BooleanField()}),
                description='Honeypot triggered; nothing stored.',
            ),
            400: OpenApiResponse(
                response=inline_serializer(name='ContactSubmitError', fields={
                    'success': serializers.BooleanField(),
                    'errors': serializers.DictField(child=serializers.ListField(child=serializers.CharField())),
                }),
                description='Validation failed.',
            ),
        },
        examples=[
            OpenApiExample(
                'Valid message',
                value={'name': 'Jane Doe', 'email': 'user@example.com',
                       'message': 'Hello, I would like to discuss a project with you.'},
                request_only=True,
            ),
            OpenApiExample('Success', value={'success': True}, response_only=True, status_codes=['201', '200']),
            OpenApiExample(
                'Validation error',
                value={'success': False, 'errors': {
                    'name': ['Name must be at least 2 characters.'],
                    'message': ['Message must be at least 10 characters.'],
                }},
                response_only=True,
                status_codes=['400'],
            ),
        ],
    )
    def post(self, request):
        # 1. Validate input
        serializer = ContactSubmissionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'success': False, 'errors': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        #Honeypot check 
        if request.data.get('website'):
            logger.warning("Honeypot triggered — silent reject")
            return Response({'success': True})

        #Extracting clean data
        name = serializer.validated_data['name']
        email = serializer.validated_data['email']
        message = serializer.validated_data['message']

        #Getting client info
        ip_address = self.get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')

        #Scoring message with ML
        spam_score = score_message(message)
        threshold = float(os.getenv('SPAM_THRESHOLD', 0.70))
        is_spam = spam_score >= threshold

        logger.info(f"Message from {email} scored {spam_score:.4f} — {'SPAM' if is_spam else 'CLEAN'}")

        #Save to database
        submission = ContactSubmission.objects.create(
            name=name,
            email=email,
            message=message,
            spam_score=spam_score,
            status='spam' if is_spam else 'accepted',
            ip_address=ip_address,
            user_agent=user_agent,
        )

        #Send email only if clean
        if not is_spam:
            email_sent = send_contact_email(submission)
            submission.email_sent = email_sent
            submission.save(update_fields=['email_sent'])

        return Response({'success': True}, status=status.HTTP_201_CREATED)

    # Helper method to get client IP address
    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')

#Health check API view
class HealthCheckView(APIView):
    @extend_schema(
        summary='Health check',
        description='Returns service status. The `ml_model` block is a fixed value; '
                    'it does not check whether the model file actually loaded.',
        tags=['Health'],
        responses=inline_serializer(name='HealthCheck', fields={
            'status': serializers.CharField(),
            'ml_model': inline_serializer(name='HealthCheckModel', fields={
                'status': serializers.CharField(),
                'ready': serializers.BooleanField(),
            }),
        }),
        examples=[
            OpenApiExample('OK', value={'status': 'ok', 'ml_model': {'status': 'loaded', 'ready': True}},
                           response_only=True),
        ],
    )
    def get(self, request):
        return Response({
            'status': 'ok',
            'ml_model': {
                'status': 'loaded',
                'ready': True
            }
        })