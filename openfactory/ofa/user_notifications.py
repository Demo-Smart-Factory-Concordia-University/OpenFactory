import openfactory.config as config


def success_msg(msg):
    """
    Success notification
    """
    print(f"{config.OFA_SUCCSESS}{msg}{config.OFA_END}")


def fail_msg(msg):
    """
    Fail notification
    """
    print(f"{config.OFA_FAIL}{msg}{config.OFA_END}")
