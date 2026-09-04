from django.shortcuts import render

# ==============================================================================
# Storefront & Catalog Views
# ==============================================================================

def home_view(request):
    """Render the main e-commerce storefront landing page."""
    return render(request,'homepage.html')
