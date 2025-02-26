def availability_color(value):
    """ Applies color for AVAILABILITY statements """
    value = (value or "").lower()
    if value == "available":
        return "LimeGreen"
    elif value == "unavailable":
        return "OrangeRed"
    return "inherit"
