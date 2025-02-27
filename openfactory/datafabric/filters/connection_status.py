def connection_status_color(value):
    """ Applies color for connection status statements """
    value = (value or "").lower()
    if value == "established":
        return "LimeGreen"
    elif value == "listen":
        return "Gold"
    elif value == "closed":
        return "OrangeRed"
    return "inherit"
