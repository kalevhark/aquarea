print('forms')

from django import forms
from .widgets import FengyuanChenDatePickerInput


class PerioodForm(forms.Form):
    start_date = forms.DateField(
        input_formats=['%d.%m.%Y'],
        widget=FengyuanChenDatePickerInput()
    )

    # Saaks saata widgetisse andmeid -> {{ widget.attrs.start }}
    start_date.widget.attrs.update({'start': 'new Date(2018, 7, 1)'})

    stopp_date = forms.DateField(
        input_formats=['%d.%m.%Y'],
        widget=FengyuanChenDatePickerInput()
    )

