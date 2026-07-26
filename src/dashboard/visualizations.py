"""
UI Layer - All visualization/chart creation functions

Design system (light, Google-style):
- Charts render transparent and sit directly on the white page (no gray boxes)
- One hue per nominal chart; multiple hues only when color encodes identity
- No gridlines; values are carried by direct labels, redundant axes are hidden
- No zoom/pan/toolbar - this is a dashboard, not an exploration tool
- Palette steps validated for colorblind-safety and contrast (see dataviz checks)
"""
import plotly.graph_objects as go
import numpy as np
from scipy import stats

# Official Google brand hues on a light surface.
# CVD separation & normal-vision floor pass; yellow sits above the lightness band
# and below 3:1 contrast by design (user's choice) - every chart direct-labels its
# values, which is the contrast relief the design system requires.
COLORS = {
    'blue': '#4285F4',
    'green': '#34A853',
    'amber': '#FBBC05',
    'yellow': '#FBBC05',
    'red': '#EA4335',
    # Text tokens (never used for marks)
    'ink': '#202124',
    'ink_2': '#5f6368',
    'ink_3': '#9aa0a6',
    'white': '#ffffff',
    # Chrome
    'border': '#dadce0',
    'surface': '#ffffff',
    # De-emphasis / context marks
    'gray_data': '#9aa0a6',
    'gray_track': '#d6dade',
}

FONT_FAMILY = "Inter, 'Google Sans', Roboto, 'Segoe UI', system-ui, sans-serif"

# Pass this to every st.plotly_chart call - kills the toolbar
PLOTLY_CONFIG = {'displayModeBar': False, 'scrollZoom': False, 'showTips': False}

HOVER_STYLE = dict(
    bgcolor=COLORS['surface'],
    bordercolor=COLORS['border'],
    font=dict(family=FONT_FAMILY, size=12, color=COLORS['ink']),
)


def _base_layout(fig, height, margin=None):
    """Shared quiet layout: transparent surfaces, locked axes, no gridlines."""
    fig.update_layout(
        height=height,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(family=FONT_FAMILY, size=12, color=COLORS['ink']),
        margin=margin or dict(l=8, r=8, t=8, b=8),
        showlegend=False,
        hoverlabel=HOVER_STYLE,
        dragmode=False,
    )
    # automargin: margins stay minimal but grow to fit tick labels (they clip otherwise)
    fig.update_xaxes(fixedrange=True, showgrid=False, zeroline=False, automargin=True)
    fig.update_yaxes(fixedrange=True, showgrid=False, zeroline=False, automargin=True)
    return fig


def create_trend_chart(df):
    """Applications per day: 2px line, soft area wash, peak directly labeled."""
    peak = df.loc[df['application_count'].idxmax()]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df['date_clean'],
        y=df['application_count'],
        mode='lines',
        line=dict(color=COLORS['blue'], width=2),
        fill='tozeroy',
        fillcolor='rgba(88, 135, 241, 0.10)',
        hovertemplate='%{y} applications<extra></extra>',
    ))

    # The one selective direct label: the peak
    fig.add_annotation(
        x=peak['date_clean'], y=peak['application_count'],
        text=f"<b>{int(peak['application_count'])}</b> · {peak['date_clean']:%b %d}",
        showarrow=True, arrowhead=0, arrowcolor=COLORS['ink_3'], arrowwidth=1,
        ax=0, ay=-28,
        font=dict(family=FONT_FAMILY, size=12, color=COLORS['ink']),
    )

    _base_layout(fig, height=360, margin=dict(l=8, r=16, t=40, b=8))
    fig.update_layout(hovermode='x unified')
    fig.update_xaxes(
        showline=True, linecolor=COLORS['border'], linewidth=1,
        ticks='outside', tickcolor=COLORS['border'],
        tickfont=dict(size=11, color=COLORS['ink_2']),
        tickformat='%b %d', nticks=8,
    )
    fig.update_yaxes(
        showline=False,
        tickfont=dict(size=11, color=COLORS['ink_2']),
        rangemode='tozero',
    )
    return fig


def create_split_bar(left_label, right_label, left_val, right_val,
                     left_color=None, height=110):
    """Proportional binary split: one bar, two segments, fully labeled.

    Left segment wears the brand hue; the remainder is neutral gray
    (not red - the right side is 'the rest', not an error state).
    """
    left_color = left_color or COLORS['green']
    total = left_val + right_val
    left_pct = left_val / total * 100
    right_pct = right_val / total * 100

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=[''], x=[left_val], orientation='h',
        marker=dict(color=left_color, line=dict(color=COLORS['surface'], width=2)),
        text=f"<b>{left_pct:.1f}%</b>" if left_pct >= 12 else '',
        textposition='inside', insidetextanchor='middle',
        textfont=dict(family=FONT_FAMILY, size=14, color='#ffffff'),
        hoverinfo='skip',
    ))
    fig.add_trace(go.Bar(
        y=[''], x=[right_val], orientation='h',
        marker=dict(color=COLORS['gray_track'], line=dict(color=COLORS['surface'], width=2)),
        # No inside label — the right segment can be too narrow to hold its
        # percent without clipping (e.g. International at 10%). Its percent
        # lives in the top-right label instead, so it always shows.
        text='',
        hoverinfo='skip',
    ))

    # Side labels above the bar ends - always fit, regardless of the split.
    # Left carries just identity + count (its % is shown inside the red
    # segment). Right carries identity + count + PERCENT in bold black, because
    # the narrow gray segment holds no inside label — this is where
    # International's percent lives, and it should read as boldly as Canada's.
    fig.add_annotation(
        x=0, y=1, xref='paper', yref='paper', xanchor='left', yanchor='bottom',
        text=f"<b>{left_label}</b> · {left_val:,}",
        showarrow=False,
        font=dict(family=FONT_FAMILY, size=13, color=COLORS['ink']),
    )
    fig.add_annotation(
        x=1, y=1, xref='paper', yref='paper', xanchor='right', yanchor='bottom',
        text=f"<b>{right_label}</b> · {right_val:,} · <b>{right_pct:.1f}%</b>",
        showarrow=False,
        font=dict(family=FONT_FAMILY, size=13, color=COLORS['ink']),
    )

    _base_layout(fig, height=height, margin=dict(l=2, r=2, t=34, b=6))
    fig.update_layout(barmode='stack', bargap=0.15, barcornerradius=6)
    fig.update_xaxes(visible=False, range=[0, total], fixedrange=True)
    fig.update_yaxes(visible=False, fixedrange=True)
    return fig


def create_hbar(df, label_col, value_col, sort_col=None, color=None, highlight=None,
                row_height=44, bargap=0.42):
    """Horizontal bars, one hue, values labeled at bar ends. X-axis hidden -
    the labels carry the values. Height fills a fixed row height per bar so the
    figure occupies its container instead of collapsing to minimum.

    `highlight` (a collection of label values) enables the self-dim treatment:
    bars whose label is in the set keep `color`; the rest are muted gray. Used
    when the chart's OWN filter dimension is active — it shows the full
    distribution (other filters still applied) with the selected bars in
    colour. None -> every bar full colour (unchanged).

    `row_height` is the vertical space (px) allotted per bar and `bargap` the
    fraction of that row left empty between bars — together they set bar
    thickness and spacing. A chart with few bars can raise both so its bars
    read as thick as a busier chart's instead of looking thin and lost in the
    container (e.g. the 2-bar Canada/International vs. the 7-bar Programs)."""

    # Plotly renders the first dataframe row at the BOTTOM, so the desired
    # top-of-chart item must sort LAST. With a sort_col (group ordering like
    # named-schools-then-tail), order by [sort_col desc, value asc] so each
    # group's biggest bar ends up highest within its block.
    if sort_col is not None:
        df = df.sort_values([sort_col, value_col], ascending=[False, True])
    else:
        df = df.sort_values(value_col, ascending=True)

    total = df[value_col].sum()
    n = len(df)
    color = color or COLORS['blue']
    bar_colors, _ = _highlight_colors(df[label_col], color, highlight)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=df[label_col], x=df[value_col], orientation='h',
        marker=dict(color=bar_colors),
        text=[f"<b>{int(v):,}</b> · {v / total * 100:.1f}%" for v in df[value_col]],
        textposition='outside', cliponaxis=False,
        textfont=dict(family=FONT_FAMILY, size=11.5, color=COLORS['ink']),
        hovertemplate='<b>%{y}</b><br>%{x:,} applicants<extra></extra>',
    ))

    _base_layout(fig, height=64 + row_height * n, margin=dict(l=8, r=16, t=8, b=8))
    fig.update_layout(bargap=bargap, barcornerradius=4)
    # leave headroom on the right so the outside labels never clip
    fig.update_xaxes(visible=False, range=[0, df[value_col].max() * 1.32])
    fig.update_yaxes(
        showline=False, ticks='',
        tickfont=dict(size=12, color=COLORS['ink_2']),
    )
    return fig


def create_column_chart(df, label_col, value_col, sort_col=None, color=None, highlight=None):
    """Vertical columns, one hue, values on the caps. Y-axis hidden -
    the labels carry the values. `highlight` enables the self-dim treatment
    (see create_hbar / _highlight_colors): selected bars keep `color`, the rest
    go muted gray. None -> all full colour."""
    if sort_col is not None:
        df = df.sort_values(sort_col)
    total = df[value_col].sum()
    color = color or COLORS['blue']
    bar_colors, _ = _highlight_colors(df[label_col], color, highlight)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df[label_col], y=df[value_col],
        marker=dict(color=bar_colors),
        text=[f"<b>{int(v):,}</b><br>{v / total * 100:.1f}%" for v in df[value_col]],
        textposition='outside', cliponaxis=False,
        textfont=dict(family=FONT_FAMILY, size=11, color=COLORS['ink']),
        hovertemplate='<b>%{x}</b><br>%{y:,} applicants<extra></extra>',
    ))

    _base_layout(fig, height=340, margin=dict(l=8, r=8, t=28, b=8))
    fig.update_layout(bargap=0.40, barcornerradius=4)
    fig.update_xaxes(
        showline=True, linecolor=COLORS['border'], linewidth=1,
        ticks='', tickfont=dict(size=11.5, color=COLORS['ink_2']),
    )
    fig.update_yaxes(visible=False, range=[0, df[value_col].max() * 1.22])
    return fig


# Ordinal blue ramp for the funnel (validated: monotone L, step gaps, light-end
# contrast, single hue). Light at the top (Applied) -> dark at the bottom
# (Completed Project), so colour intensity tracks how far people made it.
FUNNEL_RAMP = ['#8fb4f8', '#5c93f5', '#3479e0', '#1c5cc0', '#0d3f94']
# Muted gray used for funnel stages BEYOND the selected filter stage — they
# stay visible (full funnel is always shown) but read as "not in the current
# view". One flat gray for all dimmed stages; the blue ramp still encodes the
# in-scope stages.
FUNNEL_DIM_COLOR = '#d3d9e0'


def _highlight_colors(labels, base_color, highlight):
    """Self-dim helper. Given the ordered category `labels`, a `base_color`,
    and a `highlight` collection (or None), return (bar_colors, inside_text_
    colors): each label in `highlight` keeps base_color / white inside-text;
    the rest are muted gray / dark ink. highlight=None -> all base (no dim).

    Used by the categorical charts so that when a chart's OWN filter dimension
    is active it shows the full distribution with only the selected bars in
    colour (mirrors the funnel's grayed stages)."""
    labels = list(labels)
    if not highlight:
        return [base_color] * len(labels), ['#ffffff'] * len(labels)
    hi = set(highlight)
    bar = [base_color if lab in hi else FUNNEL_DIM_COLOR for lab in labels]
    txt = ['#ffffff' if lab in hi else COLORS['ink_2'] for lab in labels]
    return bar, txt


def create_funnel_chart(df, stage_col, value_col, height=420, highlight_stage=None):
    """Applicant retention funnel. Centered tapering bars (the recognizable
    funnel form), each stage labeled with its count, share of the top, and the
    stage-to-stage conversion. One ordinal blue ramp encodes progression.

    The funnel filter is "reached-at-least stage X", so when `highlight_stage`
    is given, that stage and everything BELOW it (deeper into the funnel) are
    highlighted, while the stages ABOVE it are drawn in a muted gray. The funnel
    still shows every stage's full count — the grayed stages just signal "not
    what this view is scoped to". None -> nothing dimmed (full-color funnel)."""
    df = df.sort_values('sort_order').reset_index(drop=True)
    stages = df[stage_col].tolist()
    values = df[value_col].tolist()
    top = values[0]
    n = len(values)

    # Cutoff index: the position of the highlighted stage. Stages ABOVE it
    # (earlier in the funnel) are dimmed; the stage itself and everything below
    # stay in colour. None -> nothing dimmed (full-color funnel).
    cutoff = stages.index(highlight_stage) if highlight_stage in stages else 0
    colors = [FUNNEL_RAMP[i] if i >= cutoff else FUNNEL_DIM_COLOR for i in range(n)]

    # Build hover + a rich text label per stage.
    # Stages are 5 INDEPENDENT counts (each is proof-of-reaching-that-stage,
    # not a strict subset of the one before) — under some filter combos a
    # later stage can have a HIGHER raw count than the one before it (e.g.
    # someone attended via a door scan / shipped project with no tracked
    # RSVP row). Rather than show a nonsensical ">100% from previous", clamp
    # the displayed step at 100% and surface the gap as an explicit caveat.
    texts = []
    for i, (s, v) in enumerate(zip(stages, values)):
        pct_top = v / top * 100
        if i == 0:
            texts.append(f"<b>{v:,}</b>  ·  {pct_top:.0f}% of applicants")
        else:
            prev = values[i - 1]
            step = v / prev * 100 if prev else 0
            if v > prev:
                untracked = v - prev
                texts.append(
                    f"<b>{v:,}</b>  ·  {pct_top:.0f}% of applicants  ·  100% from previous"
                    f"<br><span style='font-size:11px'>+{untracked} untracked (no {stages[i-1].lower()} record)</span>"
                )
            else:
                texts.append(f"<b>{v:,}</b>  ·  {pct_top:.0f}% of applicants  ·  {step:.0f}% from previous")

    # Text is white on the blue in-scope bars; on a dimmed (light-gray) bar
    # white would be illegible, so those stages get a muted dark ink instead.
    text_colors = ['#ffffff' if i >= cutoff else COLORS['ink_2'] for i in range(n)]

    fig = go.Figure()
    fig.add_trace(go.Funnel(
        y=stages,
        x=values,
        text=texts,
        textposition='inside',
        textinfo='text',
        textfont=dict(family=FONT_FAMILY, size=13, color=text_colors),
        marker=dict(color=colors, line=dict(color=COLORS['surface'], width=2)),
        connector=dict(line=dict(color=COLORS['border'], width=1)),
        hovertemplate='<b>%{y}</b><br>%{x:,} people<extra></extra>',
    ))

    fig.update_layout(
        height=height,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(family=FONT_FAMILY, size=13, color=COLORS['ink']),
        # generous left margin so the longest stage name ("Completed Project")
        # is never clipped; automargin then grows it further if needed
        margin=dict(l=140, r=16, t=8, b=8),
        showlegend=False,
        hoverlabel=HOVER_STYLE,
        dragmode=False,
        funnelmode='stack',
    )
    fig.update_yaxes(
        showgrid=False, zeroline=False, fixedrange=True, automargin=True,
        tickfont=dict(size=13, color=COLORS['ink'], family=FONT_FAMILY),
    )
    fig.update_xaxes(visible=False, fixedrange=True)
    return fig


def create_pie_chart(df, label_col, value_col, colors=None, height=340, highlight=None):
    """Donut chart for a small binary/categorical split. Slices carry the
    percentage; a legend names each slice. Values also shown on hover.
    `highlight` enables the self-dim treatment: slices whose label is NOT in
    the set are muted gray (mirrors create_hbar). None -> original colours."""
    total = df[value_col].sum()
    colors = colors or [COLORS['blue'], COLORS['gray_track']]
    slice_colors = list(colors[:len(df)])
    if highlight:
        hi = set(highlight)
        slice_colors = [c if lab in hi else FUNNEL_DIM_COLOR
                        for c, lab in zip(slice_colors, df[label_col])]

    fig = go.Figure()
    fig.add_trace(go.Pie(
        labels=df[label_col],
        values=df[value_col],
        hole=0.55,
        # Inset the donut so it doesn't span the full plot area — a smaller ring
        # with a band of empty space above it. The percent labels sit OUTSIDE
        # the ring; without that top clearance a thin 12-o'clock slice's label
        # (the 2.6% "Yes") rides off the top edge and clips. Shrinking the pie,
        # not the container, is what makes room for the labels.
        domain=dict(x=[0.15, 0.85], y=[0.14, 0.80]),
        marker=dict(colors=slice_colors,
                    line=dict(color=COLORS['surface'], width=2)),
        sort=False,
        direction='clockwise',
        textinfo='percent',
        texttemplate='<b>%{percent}</b>',
        textfont=dict(family=FONT_FAMILY, size=15, color=COLORS['ink']),
        textposition='outside',
        hovertemplate='<b>%{label}</b><br>%{value:,} applicants (%{percent})<extra></extra>',
    ))

    fig.update_layout(
        height=height,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(family=FONT_FAMILY, size=12, color=COLORS['ink']),
        # top room for the outside label on the topmost slice; bottom for legend
        margin=dict(l=8, r=8, t=34, b=40),
        hoverlabel=HOVER_STYLE,
        showlegend=True,
        legend=dict(orientation='h', yanchor='bottom', y=-0.15,
                    xanchor='center', x=0.5,
                    font=dict(size=12, color=COLORS['ink_2'])),
    )
    return fig


def create_response_hist(df, column_name, color):
    """Response length distribution with a normal-fit reference curve.
    Mean/sigma annotated in-chart; density axis hidden (it's a shape, not a scale)."""
    mu = df[column_name].mean()
    sigma = df[column_name].std()

    fig = go.Figure()
    fig.add_trace(go.Histogram(
        x=df[column_name],
        histnorm='probability density',
        marker=dict(color=color, opacity=0.75,
                    line=dict(color=COLORS['surface'], width=1)),
        hovertemplate='%{x} chars<extra></extra>',
    ))

    x_range = np.linspace(df[column_name].min(), df[column_name].max(), 100)
    fig.add_trace(go.Scatter(
        x=x_range, y=stats.norm.pdf(x_range, mu, sigma),
        line=dict(color=COLORS['ink_2'], width=2),
        hoverinfo='skip',
    ))

    fig.add_annotation(
        x=1, y=1, xref='paper', yref='paper', xanchor='right', yanchor='top',
        text=f"μ {mu:.0f} · σ {sigma:.0f}",
        showarrow=False,
        font=dict(family=FONT_FAMILY, size=11.5, color=COLORS['ink_2']),
    )

    _base_layout(fig, height=260, margin=dict(l=8, r=8, t=8, b=8))
    fig.update_xaxes(
        showline=True, linecolor=COLORS['border'], linewidth=1,
        ticks='outside', tickcolor=COLORS['border'],
        tickfont=dict(size=10.5, color=COLORS['ink_2']),
        title=dict(text='characters', font=dict(size=11, color=COLORS['ink_3'])),
    )
    fig.update_yaxes(visible=False)
    return fig
