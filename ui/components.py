def make_chip(text: str, color: str = "#444", bg: str = "#eee") -> str:
    return f"""
    <span style="
        display: inline-block;
        padding: 4px 8px;
        border-radius: 999px;
        background: {bg};
        color: {color};
        font-size: 0.8rem;
    ">
        {text}
    </span>
    """
