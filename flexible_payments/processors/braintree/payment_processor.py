import logging
from braintree.exceptions import AuthenticationError, AuthorizationError, DownForMaintenanceError, ServerError, \
    UpgradeRequiredError, NotFoundError
from django_fsm import TransitionNotAllowed

from flexible_payments.processors.base import PaymentProcessorBase
from flexible_payments.processors.forms import GenericTransactionForm
from flexible_payments.processors.braintree.models import BraintreePaymentMethod, BraintreeCustomer
from flexible_payments.processors.braintree.views import BraintreeTransactionView
import braintree

from flexible_payments.processors.mixins import TriggeredProcessorMixin
from flexible_payments.processors.utils import get_instance

logger = logging.getLogger(__name__)


class BraintreePaymentProcessor(PaymentProcessorBase, TriggeredProcessorMixin):
    """
    Braintree Payment Processor

    """

    form_class = GenericTransactionForm
    payment_method_class = BraintreePaymentMethod
    transaction_view_class = BraintreeTransactionView
    template_slug = 'braintree'

    _has_been_setup = False

    def __init__(self, name, *args, **kwargs):
        super(BraintreePaymentProcessor, self).__init__(name)
        if self._has_been_setup:
            return
        braintree_environments = {
            'Sandbox': braintree.Environment.Sandbox,
            'Production': braintree.Environment.Production
        }
        active_environment = kwargs.pop('environment', None)
        braintree_environment = braintree_environments[active_environment]
        braintree.Configuration.configure(braintree_environment, **kwargs)
        BraintreePaymentProcessor._has_been_setup = True

    def client_token(self):
        try:
            return braintree.ClientToken.generate()
        except (AuthenticationError, AuthorizationError, DownForMaintenanceError, ServerError, UpgradeRequiredError) as e:
            logger.warning(
                'Error generating client token %s', {
                    'error': str(e)
                }
            )

    def client_token_for_customer(self, customer):
        """
        Generates the client token for the braintree ui/fields
        :param customer:
        :return:
        """

        braintree_customer, created = BraintreeCustomer.objects.get_or_create(customer=customer)
        braintree_customer_id = braintree_customer.get('id')

        try:
            return braintree.ClientToken.generate(
                {'customer_id': braintree_customer_id}
            )
        except (AuthenticationError, AuthorizationError, DownForMaintenanceError, ServerError, UpgradeRequiredError) as e:
            logger.warning(
                'Error generating client token %s', {
                    'customer_id': braintree_customer_id,
                    'error': str(e)
                }
            )

    def refund_partial_transaction(self, transaction, amount=0):
        """

        :param transaction: the transaction to be refunded
        :param amount: the amount to be refunded
        :return: True if success, false otherwise
        """
        transaction_id = transaction.get('id')

        if not (transaction.state.SETTLED or transaction.state.SETTLING):
            return False

        try:
            return braintree.Transaction.refund(transaction_id, amount)
        except NotFoundError as e:
            logger.warning(
                'Error refunding transaction %s', {
                    'transaction_id': transaction_id,
                    'error': str(e)
                }
            )

    def refund_transaction(self, transaction):
        """

        :param transaction: the transaction to be refunded
        :return: True if success, false otherwise
        """
        transaction_id = transaction.get('id')

        if not (transaction.state.SETTLED or transaction.state.SETTLING):
            return False

        try:
            return braintree.Transaction.refund(transaction_id)
        except NotFoundError as e:
            logger.warning(
                'Error refunding transaction %s', {
                    'transaction_id': transaction_id,
                    'error': str(e)
                }
            )

    def void_transaction(self, transaction):
        """

        :param transaction: the transaction to void
        :return: True if success, false otherwise
        """
        transaction_id = transaction.get('id')

        if (transaction.state.SETTLED or transaction.state.SETTLING):
            return False

        try:
            return braintree.Transaction.void(transaction_id)
        except NotFoundError as e:
            logger.warning(
                'Error refunding transaction %s', {
                    'transaction_id': transaction_id,
                    'error': str(e)
                }
            )

    def execute_transaction(self, transaction):
        payment_processor = get_instance(transaction.payment_processor)
        if not payment_processor == self:
            return False
        if transaction.state != transaction.STATE.PENDING:
            return False
        return self._charge_transaction(transaction)

    def handle_transaction_response(self, transaction, request):
        pass

    def fetch_transaction_status(self, transaction):
        pass

    def is_payment_method_recurring(self, payment_method):
        raise NotImplementedError

    ###################
    # Private Methods #
    ###################
    def _fail_transaction(self, transaction, message):
        try:
            transaction.fail(fail_reason=message)
            transaction.save()
        except TransitionNotAllowed:
            logger.error("Couldn't fail the transaction")
        finally:
            logger.warning(message)

    def _charge_transaction(self, transaction):
        payment_method = transaction.payment_method
        if not self._is_payment_method_valid(transaction):
            return False
        if not self._is_payment_token_valid(transaction):
            return False
        payload = self._get_payment_token(payment_method)
        payload.update({
            'amount': transaction.amount
        })

    def _is_payment_method_valid(self, transaction):
        payment_method = transaction.payment_method
        if payment_method.canceled:
            self._fail_transaction(transaction, "Payment method canceled")
            return False
        if not payment_method.verified:
            self._fail_transaction(transaction, "Payment method not verified")
            return False
        return True

    def _is_payment_token_valid(self, transaction):
        payment_method = transaction.payment_method
        if not payment_method.token:
            self._fail_transaction(transaction, "Payment method has no token")
            return False
        elif not payment_method.nonce:
            self._fail_transaction(transaction, "Payment method has no nonce")
            return False
        else:
            return True

    def _get_payment_token(self, payment_method):
        if payment_method.token:
            return {'payment_method_token': payment_method.token}
        elif payment_method.nonce:
            return {'payment_method_nonce': payment_method.nonce}
        else:
            return {}

    def _update_payment_method(self, payment_method, result_details, instrument_type):
        """
        :param payment_method: A BraintreePaymentMethod.
        :param result_details: A (part of) braintreeSDK result(response)
                               containing payment method information.
        :param instrument_type: The type of the instrument (payment method);
                                see BraintreePaymentMethod.Types.
        :description: Updates a given payment method's data with data from a
                      braintreeSDK result payment method.
        """
        payment_method_details = {
            'type': instrument_type,
            'image_url': result_details.image_url,
        }

        if instrument_type == payment_method.Types.PayPal:
            payment_method_details['email'] = result_details.payer_email
            payment_method.display_info = result_details.payer_email
        elif instrument_type == payment_method.Types.CreditCard:
            payment_method_details.update({
                'card_type': result_details.card_type,
                'last_4': result_details.last_4,
            })

        payment_method.update_details(payment_method_details)

        if self.is_payment_method_recurring(payment_method):
            if result_details.token:
                payment_method.token = result_details.token
                payment_method.data.pop('nonce', None)
                payment_method.verified = True

        payment_method.save()

    def _update_transaction_status(self, transaction, result_transaction):
        """
        :param transaction: A Silver transaction with a Braintree payment method.
        :param result_transaction: A transaction from a braintreeSDK
                                   result(response).
        :description: Updates a given transaction's data with data from a
                      braintreeSDK result payment method.
        :returns True if transaction is on the happy path, False otherwise.
        """
        if not transaction.data:
            transaction.data = {}
        transaction.external_reference = result_transaction.id
        status = result_transaction.status
        transaction.data.update({
            'status': status,
            'braintree_id': result_transaction.id
        })

        target_state = None
        try:
            if status in [braintree.Transaction.Status.AuthorizationExpired,
                          braintree.Transaction.Status.SettlementDeclined,
                          braintree.Transaction.Status.Failed,
                          braintree.Transaction.Status.GatewayRejected,
                          braintree.Transaction.Status.ProcessorDeclined]:
                target_state = transaction.STATE.FAILED
                if transaction.state != target_state:
                    fail_code = self._get_fail_code(result_transaction)
                    fail_reason = self._get_braintree_fail_code(result_transaction)
                    transaction.fail(fail_code=fail_code, fail_reason=fail_reason)
                    return False
            elif status == braintree.Transaction.Status.Voided:
                target_state = transaction.STATE.CANCELED
                if transaction.state != target_state:
                    transaction.cancel()
                    return False
            elif status in [braintree.Transaction.Status.Settling,
                            braintree.Transaction.Status.SettlementPending,
                            braintree.Transaction.Status.Settled]:
                target_state = transaction.STATE.SETTLED
                if transaction.state != target_state:
                    transaction.settle()
                    return True
            else:
                return True
        except TransitionNotAllowed as e:
            logger.warning('Braintree transaction error %s' % {
                'initial_state': transaction.state,
                'target_state': target_state,
                'transaction_id': transaction.id,
                'transaction_uuid': transaction.uuid
            })
            raise e
        finally:
            transaction.save()
