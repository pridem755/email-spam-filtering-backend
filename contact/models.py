from django.db import models

#database models for contact app
class ContactSubmission(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('spam', 'Spam'),
        ('reviewed', 'Reviewed'),
    ]

    name = models.CharField(max_length=100)
    email = models.EmailField()
    message = models.TextField()
    spam_score = models.FloatField(default=0.0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    email_sent = models.BooleanField(default=False)
    reviewed_by = models.CharField(max_length=100, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} <{self.email}> — {self.status} (score: {self.spam_score})"

#Additional models for training dataset and model versions
class TrainingDataset(models.Model):
    SOURCE_CHOICES = [
        ('original', 'Original Dataset'),
        ('admin_labeled', 'Admin Labeled'),
        ('retrain', 'Retrain'),
    ]
    LABEL_CHOICES = [
        ('ham', 'Ham'),
        ('spam', 'Spam'),
    ]

    message = models.TextField()
    label = models.CharField(max_length=10, choices=LABEL_CHOICES)
    source = models.CharField(max_length=30, choices=SOURCE_CHOICES, default='original')
    confidence = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    used_in_training = models.BooleanField(default=False)
    training_run_id = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return f"[{self.label.upper()}] {self.message[:60]}..."

#Model to track different versions of the spam detection model
class ModelVersion(models.Model):
    version = models.CharField(max_length=20)
    accuracy = models.FloatField()
    f1_score = models.FloatField()
    precision = models.FloatField()
    recall = models.FloatField()
    training_samples = models.IntegerField()
    threshold = models.FloatField(default=0.70)
    model_path = models.CharField(max_length=255)
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"v{self.version} — accuracy: {self.accuracy:.2%} ({'ACTIVE' if self.is_active else 'inactive'})"
