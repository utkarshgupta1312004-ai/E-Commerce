from django.shortcuts import render


def home_view(request):
    """Render the main Cartivo e-commerce storefront homepage."""
    return render(request, 'homepage.html')
