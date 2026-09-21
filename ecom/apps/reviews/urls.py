from django.urls import path
from . import views

app_name = 'reviews'

urlpatterns = [
    # Customer Storefront Actions
    path('product/<slug:slug>/submit/', views.submit_review_view, name='submit_review'),
    path('<int:review_id>/edit/', views.edit_review_view, name='edit_review'),
    path('<int:review_id>/delete/', views.delete_review_view, name='delete_review'),
    path('<int:review_id>/vote/', views.vote_helpful_view, name='vote_helpful'),

    # Customer Account
    path('my-reviews/', views.my_reviews_view, name='my_reviews'),

    # Staff / Management Console Actions
    path('<int:review_id>/reply/', views.reply_review_view, name='reply_review'),
    path('<int:review_id>/moderate/', views.moderate_review_view, name='moderate_review'),
    path('manage/product/<int:product_id>/', views.product_reviews_manage_view, name='manage_product_reviews'),
    path('manage/all/', views.catalog_reviews_manage_view, name='manage_all_reviews'),
]
