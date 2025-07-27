from unittest import TestCase
from openfactory.models.user_notifications import UserNotifications
from openfactory.models.user_notifications import user_notify


class TestUserNotifications(TestCase):
    """
    Unit tests for UserNotifications
    """

    def test_setup(self):
        """
        Test setup method
        """
        n = UserNotifications()
        n.setup(success_msg='test success',
                fail_msg='test fail',
                info_msg='test info',
                warning_msg='test warning')
        self.assertEqual(n.success, 'test success')
        self.assertEqual(n.fail, 'test fail')
        self.assertEqual(n.info, 'test info')
        self.assertEqual(n.warning, 'test warning')

    def test_default(self):
        """
        Test default settings
        """
        n = UserNotifications()
        self.assertEqual(n.success, print)
        self.assertEqual(n.fail, print)
        self.assertEqual(n.info, print)

    def test_user_notify(self):
        """
        Test if user_notify type is UserNotifications
        """
        self.assertIsInstance(user_notify, UserNotifications)
