from flexible_payments.processors.utils import get_instance
from flexible_payments.processors.views import GenericTransactionView


class BraintreeTransactionView(GenericTransactionView):
    def get_context_data(self):
        context_data = super(BraintreeTransactionView, self).get_context_data()
        payment_processor = get_instance(self.transaction.payment_processor)
        context_data['client_token'] = payment_processor.client_token(
                self.transaction.customer
        )
        context_data['is_recurring'] = payment_processor.is_payment_method_recurring(
            self.transaction.payment_method
        )

        return context_data
