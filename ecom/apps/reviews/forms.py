from django import forms
from .models import Review, ReviewReply


class ReviewForm(forms.ModelForm):
    """
    Form for authenticated customers to submit or edit their review.
    """
    variant_id = forms.IntegerField(required=False, widget=forms.HiddenInput())

    class Meta:
        model = Review
        fields = ['rating', 'title', 'comment']
        widgets = {
            'rating': forms.RadioSelect(choices=Review.RATING_CHOICES),
            'title': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-200 bg-white text-sm text-slate-800 focus:outline-hidden focus:border-blue-500 focus:ring-1 focus:ring-blue-500',
                'placeholder': 'Summarize your experience (e.g., Fantastic quality & battery life)'
            }),
            'comment': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 bg-white text-sm text-slate-800 focus:outline-hidden focus:border-blue-500 focus:ring-1 focus:ring-blue-500',
                'rows': 4,
                'placeholder': 'What did you like or dislike? How does this product compare to your expectations?'
            }),
        }

    def clean_rating(self):
        rating = self.cleaned_data.get('rating')
        if not rating or rating < 1 or rating > 5:
            raise forms.ValidationError("Please select a valid rating between 1 and 5 stars.")
        return rating

    def clean_comment(self):
        comment = self.cleaned_data.get('comment', '').strip()
        if not comment:
            raise forms.ValidationError("Review comment is required.")
        if len(comment) < 5:
            raise forms.ValidationError("Please write at least 5 characters in your review.")
        return comment


class ReviewReplyForm(forms.ModelForm):
    """
    Form for authorized staff/sellers to submit official replies.
    """
    class Meta:
        model = ReviewReply
        fields = ['reply_text']
        widgets = {
            'reply_text': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-700 bg-slate-900 text-xs text-slate-200 focus:outline-hidden focus:border-blue-500',
                'rows': 3,
                'placeholder': 'Write an official store or seller response...'
            }),
        }
