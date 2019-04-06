from django.db import models

class UserProfile(models.Model):
    user = models.OneToOneField(User, related_name='profile', on_delete=models.CASCADE)
    phone_num = models.CharField(validators=[phone_validator], max_length=10)  # TODO: unique=True
    codename = models.CharField(max_length=50)
    # image_url = models.URLField('Image URL')

    def __str__(self):
        return self.user.first_name + " " + self.user.last_name + "'s profile"
