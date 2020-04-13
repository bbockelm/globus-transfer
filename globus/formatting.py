import click


def table(
    headers, rows, fill="", header_fmt=None, row_fmt=None, alignment=None, style=None
):
    if header_fmt is None:
        header_fmt = lambda _: _
    if row_fmt is None:
        row_fmt = lambda _: _
    if alignment is None:
        alignment = {}
    if style is None:
        style = lambda _: {}

    headers = tuple(headers)
    lengths = [len(str(h)) for h in headers]

    align_methods = [alignment.get(h, "center") for h in headers]

    processed_rows = []
    for row in rows:
        processed_rows.append([str(row.get(key, fill)) for key in headers])

    for row in processed_rows:
        lengths = [max(curr, len(entry)) for curr, entry in zip(lengths, row)]

    header = header_fmt(
        "  ".join(
            getattr(str(h), a)(l) for h, l, a in zip(headers, lengths, align_methods)
        ).rstrip()
    )

    lines = [
        click.style(
            row_fmt(
                "  ".join(
                    getattr(f, a)(l) for f, l, a in zip(row, lengths, align_methods)
                )
            ),
            **style(original_row),
        )
        for original_row, row in zip(rows, processed_rows)
    ]

    output = "\n".join([header] + lines)

    return output
