from django import forms
from .models import Stock, Warehouse, Location, StockAdjustment
from apps.catalog.models import Product, ProductVariant


class StockAdjustmentForm(forms.ModelForm):
    product = forms.ModelChoiceField(
        queryset=Product.objects.filter(is_active=True).order_by('title'),
        required=True,
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-200 focus:outline-hidden focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 text-sm font-medium bg-white text-slate-900',
            'id': 'adjustment-product-select'
        })
    )
    warehouse = forms.ModelChoiceField(
        queryset=Warehouse.objects.filter(status='ACTIVE').order_by('name'),
        required=True,
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-200 focus:outline-hidden focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 text-sm font-medium bg-white text-slate-900'
        })
    )
    quantity = forms.IntegerField(
        min_value=1,
        initial=1,
        widget=forms.NumberInput(attrs={
            'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-200 focus:outline-hidden focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 text-sm font-medium bg-white text-slate-900',
            'placeholder': 'Quantity to adjust'
        })
    )

    class Meta:
        model = StockAdjustment
        fields = ['adjustment_type', 'reason', 'notes']
        widgets = {
            'adjustment_type': forms.Select(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-200 focus:outline-hidden focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 text-sm font-medium bg-white text-slate-900'
            }),
            'reason': forms.Select(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-200 focus:outline-hidden focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 text-sm font-medium bg-white text-slate-900'
            }),
            'notes': forms.Textarea(attrs={
                'rows': 3,
                'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-200 focus:outline-hidden focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 text-sm font-medium bg-white text-slate-900',
                'placeholder': 'Optional internal auditing remarks or reconciliation ticket #'
            }),
        }


class StockTransferForm(forms.Form):
    product = forms.ModelChoiceField(
        queryset=Product.objects.filter(is_active=True).order_by('title'),
        required=True,
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-200 focus:outline-hidden focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 text-sm font-medium bg-white text-slate-900'
        })
    )
    source_warehouse = forms.ModelChoiceField(
        queryset=Warehouse.objects.filter(status='ACTIVE').order_by('name'),
        required=True,
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-200 focus:outline-hidden focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 text-sm font-medium bg-white text-slate-900'
        })
    )
    dest_warehouse = forms.ModelChoiceField(
        queryset=Warehouse.objects.filter(status='ACTIVE').order_by('name'),
        required=True,
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-200 focus:outline-hidden focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 text-sm font-medium bg-white text-slate-900'
        })
    )
    quantity = forms.IntegerField(
        min_value=1,
        initial=1,
        widget=forms.NumberInput(attrs={
            'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-200 focus:outline-hidden focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 text-sm font-medium bg-white text-slate-900'
        })
    )
    reason = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-200 focus:outline-hidden focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 text-sm font-medium bg-white text-slate-900',
            'placeholder': 'e.g. Rebalancing regional fulfillment center stock'
        })
    )

    def clean(self):
        cleaned_data = super().clean()
        src = cleaned_data.get('source_warehouse')
        dst = cleaned_data.get('dest_warehouse')
        if src and dst and src == dst:
            raise forms.ValidationError("Source and destination warehouses cannot be identical.")
        return cleaned_data
