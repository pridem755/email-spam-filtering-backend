from django.test import TestCase, Client
from django.urls import reverse
from unittest.mock import patch, MagicMock
from contact.models import ContactSubmission, TrainingDataset, ModelVersion
from contact.serializers import ContactSubmissionSerializer
from contact.ml_engine import score_message, load_model
from contact.email_service import send_contact_email
import os
import json

#============================================================================
#MODEL TESTS
#============================================================================

#Test ContactSubmission model creation and validation.
class ContactSubmissionModelTest(TestCase):
    def setUp(self):
        """Create test data."""
        self.submission = ContactSubmission.objects.create(
            name="John Doe",
            email="john@example.com",
            message="This is a test message",
            spam_score=0.25,
            status="accepted"
        )

    #Test that ContactSubmission is created correctly.
    def test_contact_submission_creation(self):
        self.assertEqual(self.submission.name, "John Doe")
        self.assertEqual(self.submission.email, "john@example.com")
        self.assertEqual(self.submission.spam_score, 0.25)
        self.assertEqual(self.submission.status, "accepted")
        self.assertFalse(self.submission.email_sent)

    #Test string representation.
    def test_contact_submission_str(self):
        expected = f"John Doe <john@example.com> — accepted (score: 0.25)"
        self.assertEqual(str(self.submission), expected)
    
    #Test default field values.
    def test_default_values(self):
        submission = ContactSubmission.objects.create(
            name="Test User",
            email="test@example.org",
            message="Test"
        )
        self.assertEqual(submission.spam_score, 0.0)
        self.assertEqual(submission.status, "pending")
        self.assertFalse(submission.email_sent)
        self.assertEqual(submission.notes, "")

#Test TrainingDataset model.
class TrainingDatasetModelTest(TestCase):
    def test_training_dataset_creation(self):
        #Test TrainingDataset creation.
        data = TrainingDataset.objects.create(
            message="Free money! Click here!",
            label="spam",
            source="admin_labeled",
            confidence=0.95
        )
        self.assertEqual(data.label, "spam")
        self.assertEqual(data.source, "admin_labeled")
        self.assertFalse(data.used_in_training)

#Test ModelVersion model.
class ModelVersionTest(TestCase):
    
    def test_model_version_creation(self):
        """Test ModelVersion creation."""
        version = ModelVersion.objects.create(
            version="v1.0",
            accuracy=0.972,
            f1_score=0.973,
            precision=0.971,
            recall=0.975,
            training_samples=76000,
            threshold=0.70,
            model_path="models/spam_classifier_v1.joblib",
            is_active=True
        )
        self.assertEqual(version.version, "v1.0")
        self.assertTrue(version.is_active)

#============================================================================
#SERIALIZER TESTS
#============================================================================
class ContactSubmissionSerializerTest(TestCase):
    """Test ContactSubmissionSerializer validation."""
    
    def test_valid_data(self):
        """Test serializer with valid data."""
        data = {
            "name": "Jane Smith",
            "email": "jane@example.com",
            "message": "I would like to discuss opportunities."
        }
        serializer = ContactSubmissionSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data['name'], "Jane Smith")
    
    def test_name_too_short(self):
        """Test name validation (minimum 2 characters)."""
        data = {
            "name": "J",
            "email": "j@example.com",
            "message": "This is a test message."
        }
        serializer = ContactSubmissionSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('name', serializer.errors)
    
    def test_invalid_email(self):
        """Test email validation."""
        data = {
            "name": "John Doe",
            "email": "not-an-email",
            "message": "This is a test message."
        }
        serializer = ContactSubmissionSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('email', serializer.errors)
    
    def test_message_too_short(self):
        """Test message validation (minimum 10 characters)."""
        data = {
            "name": "John Doe",
            "email": "john@example.com",
            "message": "Hi"
        }
        serializer = ContactSubmissionSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('message', serializer.errors)
    
    def test_message_too_long(self):
        """Test message validation (maximum 5000 characters)."""
        data = {
            "name": "John Doe",
            "email": "john@example.com",
            "message": "x" * 5001
        }
        serializer = ContactSubmissionSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('message', serializer.errors)
    
    def test_whitespace_stripping(self):
        """Test that whitespace is stripped from inputs."""
        data = {
            "name": "  John Doe  ",
            "email": "  john@example.com  ",
            "message": "  This is a test message.  "
        }
        serializer = ContactSubmissionSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data['name'], "John Doe")
        self.assertEqual(serializer.validated_data['email'], "john@example.com")

#============================================================================
# ML ENGINE TESTS
#============================================================================

class MLEngineTest(TestCase):
    """Test ML scoring engine."""
    
    def test_score_message_no_model(self):
        """Test scoring when no model is loaded (should return 0.0)."""
        # Temporarily set MODEL_PATH to non-existent file
        with patch.dict(os.environ, {'MODEL_PATH': 'nonexistent.joblib'}):
            score = score_message("This is a test message")
            self.assertEqual(score, 0.0)
    
    @patch('contact.ml_engine.load_model')
    def test_score_message_with_mock_model(self, mock_load):
        """Test scoring with mocked model."""
        # Mock the model
        mock_model = MagicMock()
        mock_model.predict_proba.return_value = [[0.3, 0.7]]  # 70% spam
        mock_load.return_value = mock_model
        
        score = score_message("WINNER! Free money!")
        
        # Should return spam probability (index 1)
        self.assertEqual(score, 0.7)
        mock_model.predict_proba.assert_called_once()

#============================================================================  
# EMAIL SERVICE TESTS
#============================================================================
class EmailServiceTest(TestCase):
    """Test email sending functionality."""
    
    def setUp(self):
        """Create test submission."""
        self.submission = ContactSubmission.objects.create(
            name="Test User",
            email="test@example.com",
            message="This is a test message",
            spam_score=0.25,
            status="accepted"
        )
    
    @patch('contact.email_service.resend.Emails.send')
    @patch.dict(os.environ, {'RESEND_API_KEY': 'test_key', 'OWNER_EMAIL': 'owner@example.org'})
    def test_send_email_success(self, mock_send):
        """Test successful email sending."""
        mock_send.return_value = {'id': 'test_email_id'}
        
        result = send_contact_email(self.submission)
        
        self.assertTrue(result)
        mock_send.assert_called_once()
        
        # Verify email content
        call_args = mock_send.call_args[1]
        self.assertEqual(mock_send.call_count, 1)
    
    @patch.dict(os.environ, {'RESEND_API_KEY': ''})
    def test_send_email_no_api_key(self):
        """Test email sending when API key is missing."""
        result = send_contact_email(self.submission)
        self.assertFalse(result)
    
    @patch('contact.email_service.resend.Emails.send')
    @patch.dict(os.environ, {'RESEND_API_KEY': 'test_key'})
    def test_send_email_failure(self, mock_send):
        """Test email sending when Resend API fails."""
        mock_send.side_effect = Exception("API Error")
        
        result = send_contact_email(self.submission)
        self.assertFalse(result)

#============================================================================
# API VIEW TEST
#============================================================================
class ContactSubmitViewTest(TestCase):
    """Test contact submission API endpoint."""
    
    def setUp(self):
        """Set up test client."""
        self.client = Client()
        self.url = reverse('contact-submit')
    
    @patch('contact.views.score_message')
    @patch('contact.views.send_contact_email')
    def test_valid_submission(self, mock_email, mock_score):
        """Test valid contact form submission."""
        mock_score.return_value = 0.25  # Low spam score
        mock_email.return_value = True
        
        data = {
            "name": "John Doe",
            "email": "john@example.com",
            "message": "I would like to discuss opportunities."
        }
        
        response = self.client.post(
            self.url,
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json(), {'success': True})
        
        # Verify database entry
        submission = ContactSubmission.objects.get(email="john@example.com")
        self.assertEqual(submission.name, "John Doe")
        self.assertEqual(submission.spam_score, 0.25)
        self.assertEqual(submission.status, "accepted")
        self.assertTrue(submission.email_sent)
    
    @patch('contact.views.score_message')
    @patch('contact.views.send_contact_email')
    def test_spam_submission(self, mock_email, mock_score):
        """Test submission flagged as spam."""
        mock_score.return_value = 0.85  # High spam score
        
        data = {
            "name": "Spammer",
            "email": "spam@example.org",
            "message": "WINNER! Click here for free money!"
        }
        
        response = self.client.post(
            self.url,
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 201)
        
        # Verify database entry
        submission = ContactSubmission.objects.get(email="spam@example.org")
        self.assertEqual(submission.status, "spam")
        self.assertFalse(submission.email_sent)
        
        # Email should NOT be called
        mock_email.assert_not_called()
    
    def test_invalid_data(self):
        """Test submission with invalid data."""
        data = {
            "name": "J",  # Too short
            "email": "not-an-email",  # Invalid
            "message": "Hi"  # Too short
        }
        
        response = self.client.post(
            self.url,
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()['success'])
        self.assertIn('errors', response.json())
    
    def test_honeypot_detection(self):
        """Test honeypot field detection."""
        data = {
            "name": "Bot",
            "email": "bot@example.org",
            "message": "This is spam",
            "website": "http://example.org" 
        }
        
        response = self.client.post(
            self.url,
            data=json.dumps(data),
            content_type='application/json'
        )
        
        # Should return success but not save to database
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'success': True})
        
        # Verify NOT saved to database
        self.assertEqual(ContactSubmission.objects.filter(email="bot@example.org").count(), 0)
    
    @patch('contact.views.score_message')
    def test_ip_address_captured(self, mock_score):
        """Test that IP address is captured."""
        mock_score.return_value = 0.25
        
        data = {
            "name": "Test User",
            "email": "test@example.org",
            "message": "Test message for IP capture"
        }
        
        response = self.client.post(
            self.url,
            data=json.dumps(data),
            content_type='application/json',
            REMOTE_ADDR='192.168.1.1'
        )
        
        submission = ContactSubmission.objects.get(email="test@example.org")
        self.assertIsNotNone(submission.ip_address)


class HealthCheckViewTest(TestCase):
    """Test health check endpoint."""
    
    def test_health_check(self):
        """Test health check returns OK."""
        response = self.client.get(reverse('health-check'))
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'ok')
        self.assertIn('ml_model', data)

#============================================================================
# INTEGRATION TESTS
#============================================================================

class EndToEndFlowTest(TestCase):
    """Test complete end-to-end flow."""
    
    @patch('contact.views.score_message')
    @patch('contact.views.send_contact_email')
    def test_complete_clean_message_flow(self, mock_email, mock_score):
        """Test complete flow for clean message."""
        mock_score.return_value = 0.15
        mock_email.return_value = True
        
        #Submit message
        data = {
            "name": "Recruiter",
            "email": "hr@example.com",
            "message": "Hi Jane, we'd like to discuss opportunities at our company."
        }
        
        response = self.client.post(
            reverse('contact-submit'),
            data=json.dumps(data),
            content_type='application/json'
        )
        
        #Verify response
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.json()['success'])
        
        #Verify database
        submission = ContactSubmission.objects.get(email="hr@example.com")
        self.assertEqual(submission.spam_score, 0.15)
        self.assertEqual(submission.status, "accepted")
        self.assertTrue(submission.email_sent)
        
        #Verify email was sent
        mock_email.assert_called_once_with(submission)
    
    @patch('contact.views.score_message')
    def test_complete_spam_message_flow(self, mock_score):
        """Test complete flow for spam message."""
        mock_score.return_value = 0.95
        
        #Submit spam
        data = {
            "name": "Spammer",
            "email": "spam@example.org",
            "message": "URGENT! You won $10000! Click now!"
        }
        
        response = self.client.post(
            reverse('contact-submit'),
            data=json.dumps(data),
            content_type='application/json'
        )
        
        #Verify blocked
        submission = ContactSubmission.objects.get(email="spam@example.org")
        self.assertEqual(submission.status, "spam")
        self.assertFalse(submission.email_sent)

#TEST RUNNER
if __name__ == '__main__':
    import django
    from django.conf import settings
    from django.test.utils import get_runner
    
    django.setup()
    TestRunner = get_runner(settings)
    test_runner = TestRunner()
    failures = test_runner.run_tests(['contact'])
    
    if failures:
        exit(1)

