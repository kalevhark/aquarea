from django.forms import DateInput


class FengyuanChenDatePickerInput(DateInput):
    template_name = 'widgets/fengyuanchen_datepicker.html'

    def get_context(self, name, value, attrs):
        context = super(FengyuanChenDatePickerInput, self).get_context(name, value, attrs)
        # context['start'] = 'new Date(2018, 7, 1)'
        return context