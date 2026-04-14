"""
Módulo de gráficas dinámicas e interactivas.
Genera figuras de matplotlib para embeber en la UI de tkinter.
Todas las funciones devuelven objetos Figure de matplotlib.

Mejoras visuales v2:
  - seaborn para heatmaps (cell borders, anotaciones, colorbars bonitas)
  - rcParams globales: ejes sin spines top/right, grid suave, tipografía
  - KDE overlay en histogramas (numpy puro, sin scipy)
  - Indicadores semicirculares (half-donut) para predicciones
  - Relleno degradado bajo líneas temporales
  - Paleta de colores más viva y consistente
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.figure import Figure
from matplotlib.gridspec import GridSpec
import matplotlib.ticker as mticker
import numpy as np

try:
    import seaborn as sns
    _HAS_SEABORN = True
except ImportError:
    _HAS_SEABORN = False


# ============================================================
# Paleta de colores
# ============================================================

COLORS = {
    "alto":      "#e74c3c",
    "medio":     "#f39c12",
    "bajo":      "#27ae60",
    "primary":   "#2563eb",
    "secondary": "#7c3aed",
    "accent":    "#0891b2",
    "accent2":   "#ea580c",
    "neutral":   "#64748b",
    "bg":        "#f0f4f8",
    "bg_card":   "#ffffff",
    "text":      "#1e293b",
    "grid":      "#e2e8f0",
    "border":    "#cbd5e1",
    "fg_dim":    "#64748b",
}

RISK_PALETTE = [COLORS["bajo"], COLORS["medio"], COLORS["alto"]]

# ── rcParams globales: apariencia limpia y moderna ───────────────────────
plt.rcParams.update({
    "font.family":          "DejaVu Sans",
    "font.size":            9,
    "axes.titlesize":       11,
    "axes.titleweight":     "bold",
    "axes.labelsize":       8.5,
    "xtick.direction":      "out",
    "ytick.direction":      "out",
    "xtick.labelsize":      8,
    "ytick.labelsize":      8,
    "lines.linewidth":      2.0,
    "lines.solid_capstyle": "round",
    "legend.framealpha":    0.9,
    "legend.fontsize":      8,
    "legend.borderpad":     0.5,
    "figure.dpi":           100,
    "savefig.dpi":          150,
    "savefig.bbox":         "tight",
})


# ============================================================
# Helpers internos
# ============================================================

def _apply_dark_style(fig: Figure, axes=None):
    """
    Aplica tema oscuro a la figura y sus ejes.
    Mejoras v2: oculta spines top/right, set_axisbelow, grid más suave.
    """
    fig.patch.set_facecolor(COLORS["bg"])
    ax_list = axes if axes is not None else fig.get_axes()
    if not isinstance(ax_list, (list, tuple, np.ndarray)):
        ax_list = [ax_list]
    for ax in ax_list:
        ax.set_facecolor(COLORS["bg_card"])
        ax.tick_params(colors=COLORS["text"], labelsize=8, length=3, width=0.6)
        ax.xaxis.label.set_color(COLORS["text"])
        ax.yaxis.label.set_color(COLORS["text"])
        ax.title.set_color(COLORS["text"])
        # Spines: solo izquierda y abajo, más suaves
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_edgecolor(COLORS["grid"])
        ax.spines["left"].set_linewidth(0.8)
        ax.spines["bottom"].set_edgecolor(COLORS["grid"])
        ax.spines["bottom"].set_linewidth(0.8)
        # Grid detrás de los datos
        ax.grid(color=COLORS["grid"], linestyle="-", linewidth=0.4, alpha=0.5)
        ax.set_axisbelow(True)


def _kde_line(values: list, x_min: float = 0, x_max: float = 100,
              bandwidth: float = 8, n_points: int = 300):
    """
    KDE gaussiana simple (numpy puro, sin scipy).
    Devuelve (x, y_density) escalado a nº de observaciones × ancho de bin.
    """
    if len(values) < 2:
        return np.array([]), np.array([])
    x = np.linspace(x_min, x_max, n_points)
    bin_width = (x_max - x_min) / 10.0  # 10 bins
    y = np.zeros_like(x)
    for v in values:
        y += np.exp(-0.5 * ((x - v) / bandwidth) ** 2)
    # Normalizar a densidad de probabilidad y re-escalar a frecuencia
    y /= (len(values) * bandwidth * np.sqrt(2 * np.pi))
    y *= len(values) * bin_width
    return x, y


def _draw_semicircle_gauge(ax, value_pct: float, color: str,
                            title: str, sublabel: str = ""):
    """
    Dibuja un indicador semicircular (half-donut) elegante.
    value_pct: 0-100. El arco se rellena de izquierda a derecha por arriba.
    """
    frac = max(0.0, min(1.0, value_pct / 100.0))
    # Tres sectores: [relleno, vacío_superior, semicírculo_inferior_oculto]
    # Total normalizado = 2.0 (top half = 1.0, bottom half = 1.0)
    sizes = [max(frac, 0.001), max(1.0 - frac, 0.001), 1.0]
    pie_colors = [color, COLORS["border"], COLORS["bg"]]

    wedges, _ = ax.pie(
        sizes,
        colors=pie_colors,
        startangle=180,
        counterclock=False,
        wedgeprops={"width": 0.38, "edgecolor": COLORS["bg"], "linewidth": 1.5},
        radius=1.0,
    )
    # Ocultar la mitad inferior
    wedges[2].set_alpha(0.0)

    # Recortar vista: solo mostrar la mitad superior
    ax.set_xlim(-1.35, 1.35)
    ax.set_ylim(-0.22, 1.25)

    # Texto central: valor
    ax.text(0, 0.32, f"{value_pct:.0f}%",
            ha="center", va="center",
            fontsize=22, fontweight="bold", color=color)
    ax.text(0, 0.02, title,
            ha="center", va="center",
            fontsize=9, color=COLORS["text"], fontweight="bold")
    if sublabel:
        ax.text(0, -0.14, sublabel,
                ha="center", va="center",
                fontsize=7.5, color=COLORS["fg_dim"], style="italic")

    # Etiquetas extremos
    ax.text(-1.2, -0.12, "0%", ha="center", fontsize=7, color=COLORS["fg_dim"])
    ax.text( 1.2, -0.12, "100%", ha="center", fontsize=7, color=COLORS["fg_dim"])
    ax.axis("off")


def _style_seaborn_colorbar(ax):
    """Aplica tema oscuro a la colorbar generada por seaborn."""
    try:
        cbar = ax.collections[0].colorbar
        if cbar is not None:
            cbar.ax.set_facecolor(COLORS["bg"])
            cbar.ax.tick_params(colors=COLORS["text"], labelsize=7, length=2)
            plt.setp(cbar.ax.yaxis.get_ticklabels(), color=COLORS["text"])
            for spine in cbar.ax.spines.values():
                spine.set_edgecolor(COLORS["grid"])
    except (IndexError, AttributeError):
        pass


# ============================================================
# Gráficas de Dashboard de curso
# ============================================================

def chart_risk_donut(course_metrics: Dict, figsize=(4, 4)) -> Figure:
    """Gráfica de donut con distribución de niveles de riesgo."""
    high   = course_metrics.get("at_risk_high",   0)
    medium = course_metrics.get("at_risk_medium",  0)
    low    = course_metrics.get("at_risk_low",     0)
    total  = high + medium + low

    fig, ax = plt.subplots(figsize=figsize)
    _apply_dark_style(fig, ax)
    ax.spines["bottom"].set_visible(False)
    ax.spines["left"].set_visible(False)
    ax.set_xticks([])
    ax.set_yticks([])

    if total == 0:
        ax.text(0.5, 0.5, "Sin datos", transform=ax.transAxes,
                ha="center", va="center", color=COLORS["text"], fontsize=12)
        ax.set_title("Distribución de Riesgo", fontsize=11, fontweight="bold",
                     color=COLORS["text"])
        return fig

    values  = [low, medium, high]
    labels  = [f"Bajo\n{low}", f"Medio\n{medium}", f"Alto\n{high}"]
    colors  = [COLORS["bajo"], COLORS["medio"], COLORS["alto"]]
    explode = (0, 0.04, 0.08)

    wedges, texts, autotexts = ax.pie(
        values,
        labels=labels,
        autopct="%1.0f%%",
        colors=colors,
        explode=explode,
        startangle=90,
        pctdistance=0.78,
        wedgeprops={"linewidth": 2.5, "edgecolor": COLORS["bg"]},
        shadow=False,
    )
    for txt in texts:
        txt.set_color(COLORS["text"])
        txt.set_fontsize(8)
        txt.set_fontweight("bold")
    for at in autotexts:
        at.set_color("white")
        at.set_fontsize(8.5)
        at.set_fontweight("bold")

    # Agujero central
    circle = plt.Circle((0, 0), 0.54, color=COLORS["bg_card"])
    ax.add_patch(circle)
    ax.text(0,  0.12, str(total), ha="center", va="center",
            fontsize=26, fontweight="bold", color=COLORS["text"])
    ax.text(0, -0.12, "alumnos", ha="center", va="center",
            fontsize=8.5, color=COLORS["fg_dim"])

    ax.set_title("Distribución de Riesgo", fontsize=11, fontweight="bold",
                 color=COLORS["text"], pad=12)
    fig.tight_layout()
    return fig


def chart_engagement_histogram(all_students: List[Dict], figsize=(5, 3.5)) -> Figure:
    """
    Histograma de distribución del engagement con curva KDE suave.
    Barras coloreadas por nivel de riesgo (rojo/naranja/verde).
    """
    fig, ax = plt.subplots(figsize=figsize)
    _apply_dark_style(fig, ax)

    values = [s["metrics"].get("engagement_score", 0)
              for s in all_students if "metrics" in s]
    if not values:
        ax.text(0.5, 0.5, "Sin datos", transform=ax.transAxes,
                ha="center", va="center", color=COLORS["text"])
        ax.set_title("Distribución de Engagement", fontsize=11, fontweight="bold",
                     color=COLORS["text"])
        return fig

    bins = np.linspace(0, 100, 11)
    n, bins_out, patches = ax.hist(
        values, bins=bins,
        edgecolor=COLORS["bg"], linewidth=0.6, alpha=0.85, zorder=2,
    )
    # Colorear por riesgo
    for patch, left in zip(patches, bins_out[:-1]):
        if left < 30:
            patch.set_facecolor(COLORS["alto"])
        elif left < 60:
            patch.set_facecolor(COLORS["medio"])
        else:
            patch.set_facecolor(COLORS["bajo"])

    # KDE suave (numpy puro)
    if len(values) >= 3:
        x_k, y_k = _kde_line(values, x_min=0, x_max=100, bandwidth=9)
        if len(x_k):
            ax.plot(x_k, y_k, color=COLORS["text"], linewidth=2,
                    alpha=0.75, zorder=5, label="Densidad")
            ax.fill_between(x_k, y_k, alpha=0.08, color=COLORS["text"], zorder=4)

    # Línea de media
    mean_val = float(np.mean(values))
    ax.axvline(mean_val, color=COLORS["accent"], linestyle="--", linewidth=1.8,
               label=f"Media: {mean_val:.0f}", zorder=6)
    ax.legend(facecolor=COLORS["bg_card"], labelcolor=COLORS["text"],
              fontsize=8, framealpha=0.9)

    ax.set_xlabel("Índice de Engagement (0-100)")
    ax.set_ylabel("N.º Alumnos")
    ax.set_title("Distribución de Engagement", fontsize=11, fontweight="bold",
                 color=COLORS["text"])
    ax.set_xlim(0, 100)
    fig.tight_layout()
    return fig


def chart_grade_distribution(course_metrics: Dict, figsize=(5, 3.5)) -> Figure:
    """Barras con distribución de calificaciones, etiquetas flotantes."""
    fig, ax = plt.subplots(figsize=figsize)
    _apply_dark_style(fig, ax)

    dist   = course_metrics.get("grade_distribution", {})
    labels = list(dist.keys())
    values = list(dist.values())

    if not any(values):
        ax.text(0.5, 0.5, "Sin datos de calificaciones", transform=ax.transAxes,
                ha="center", va="center", color=COLORS["text"], fontsize=10)
        ax.set_title("Distribución de Calificaciones", fontsize=11, fontweight="bold",
                     color=COLORS["text"])
        return fig

    bar_colors = [
        COLORS["alto"], COLORS["alto"], COLORS["medio"],
        COLORS["bajo"], COLORS["bajo"],
    ]
    bars = ax.bar(labels, values, color=bar_colors,
                  edgecolor=COLORS["bg"], linewidth=0.6, alpha=0.88,
                  width=0.65, zorder=2)

    # Etiquetas sobre las barras
    for bar, val in zip(bars, values):
        if val > 0:
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.15,
                str(int(val)),
                ha="center", va="bottom",
                color=COLORS["text"], fontsize=9.5, fontweight="bold",
            )

    ax.set_xlabel("Rango de Nota (%)")
    ax.set_ylabel("N.º Alumnos")
    ax.set_title("Distribución de Calificaciones", fontsize=11, fontweight="bold",
                 color=COLORS["text"])
    ax.set_ylim(0, max(values) * 1.28 + 1 if values else 5)
    fig.tight_layout()
    return fig


def chart_scatter_engagement_vs_grade(all_students: List[Dict],
                                       figsize=(5, 4)) -> Figure:
    """
    Scatter engagement vs calificación.
    Usa seaborn.scatterplot si disponible (mejora los markers).
    Añade banda de confianza sombreada alrededor de la tendencia.
    """
    fig, ax = plt.subplots(figsize=figsize)
    _apply_dark_style(fig, ax)

    xs, ys, risk_levels = [], [], []
    for s in all_students:
        m    = s.get("metrics", {})
        eng  = m.get("engagement_score")
        grade= m.get("final_grade_pct")
        risk = s.get("risk_level", "bajo")
        if eng is None or grade is None:
            continue
        xs.append(eng)
        ys.append(grade)
        risk_levels.append(risk)

    if not xs:
        ax.text(0.5, 0.5, "Sin datos suficientes",
                transform=ax.transAxes, ha="center", va="center",
                color=COLORS["text"], fontsize=10)
        ax.set_title("Engagement vs Calificación", fontsize=11, fontweight="bold",
                     color=COLORS["text"])
        return fig

    # Puntos coloreados por riesgo
    for eng, grade, risk in zip(xs, ys, risk_levels):
        color = COLORS.get(risk, COLORS["neutral"])
        ax.scatter(eng, grade, c=color, alpha=0.82, s=70,
                   edgecolors=COLORS["bg"], linewidths=0.6, zorder=3)

    # Línea de tendencia + banda de confianza sombreada
    if len(xs) >= 4:
        xs_arr = np.array(xs)
        ys_arr = np.array(ys)
        z = np.polyfit(xs_arr, ys_arr, 1)
        p = np.poly1d(z)
        x_line = np.linspace(min(xs_arr), max(xs_arr), 200)
        y_line = p(x_line)
        # Residuals std para banda
        residuals = ys_arr - p(xs_arr)
        std = float(np.std(residuals))
        ax.plot(x_line, y_line, color=COLORS["primary"],
                linestyle="--", linewidth=2, alpha=0.9, label="Tendencia", zorder=4)
        ax.fill_between(x_line, y_line - std, y_line + std,
                        alpha=0.12, color=COLORS["primary"], zorder=2)

    legend_patches = [
        mpatches.Patch(color=COLORS["bajo"],  label="Riesgo Bajo"),
        mpatches.Patch(color=COLORS["medio"], label="Riesgo Medio"),
        mpatches.Patch(color=COLORS["alto"],  label="Riesgo Alto"),
    ]
    if len(xs) >= 4:
        legend_patches.append(
            mpatches.Patch(color=COLORS["primary"], alpha=0.6, label="Tendencia ±σ")
        )
    ax.legend(handles=legend_patches, facecolor=COLORS["bg_card"],
              labelcolor=COLORS["text"], fontsize=8, loc="upper left")

    ax.set_xlabel("Engagement (0-100)")
    ax.set_ylabel("Calificación (%)")
    ax.set_title("Engagement vs Calificación", fontsize=11, fontweight="bold",
                 color=COLORS["text"])
    ax.set_xlim(-5, 105)
    ax.set_ylim(-5, 105)
    fig.tight_layout()
    return fig


def chart_activity_heatmap(all_students: List[Dict], figsize=(6, 4)) -> Figure:
    """
    Heatmap de actividad: alumnos × métricas.
    Usa seaborn.heatmap si disponible (cell lines, colorbars bonitas).
    """
    metrics_keys = [
        ("engagement_score", "Engagement"),
        ("completion_rate",  "Completitud"),
        ("submission_rate",  "Entregas"),
        ("on_time_rate",     "A tiempo"),
        ("quiz_avg_pct",     "Cuestion."),
        ("academic_score",   "Académico"),
    ]

    students_sorted = sorted(
        all_students, key=lambda s: s.get("risk_level", "bajo"), reverse=True
    )[:30]

    fig, ax = plt.subplots(figsize=figsize)

    if not students_sorted:
        _apply_dark_style(fig, ax)
        ax.text(0.5, 0.5, "Sin datos", transform=ax.transAxes,
                ha="center", va="center", color=COLORS["text"])
        return fig

    names      = [s.get("fullname", "?")[:20] for s in students_sorted]
    col_labels = [lbl for _, lbl in metrics_keys]
    data_arr   = np.array([
        [s.get("metrics", {}).get(k) or 0 for k, _ in metrics_keys]
        for s in students_sorted
    ], dtype=float)

    do_annot = len(students_sorted) <= 15

    if _HAS_SEABORN:
        fig.patch.set_facecolor(COLORS["bg"])
        ax.set_facecolor(COLORS["bg_card"])

        sns.heatmap(
            data_arr,
            xticklabels=col_labels,
            yticklabels=names,
            cmap="RdYlGn",
            vmin=0, vmax=100,
            annot=do_annot,
            fmt=".0f",
            annot_kws={"size": 6, "color": COLORS["text"], "weight": "bold"},
            linewidths=0.4,
            linecolor=COLORS["bg"],
            ax=ax,
            cbar_kws={"shrink": 0.75, "aspect": 28},
        )
        ax.set_facecolor(COLORS["bg_card"])
        ax.tick_params(colors=COLORS["text"], labelsize=7, length=0)
        ax.set_xticklabels(ax.get_xticklabels(), rotation=35, ha="right",
                           color=COLORS["text"], fontsize=8)
        ax.set_yticklabels(ax.get_yticklabels(), color=COLORS["text"], fontsize=7)
        _style_seaborn_colorbar(ax)
    else:
        _apply_dark_style(fig, ax)
        im = ax.imshow(data_arr, cmap="RdYlGn", aspect="auto", vmin=0, vmax=100)
        ax.set_xticks(range(len(col_labels)))
        ax.set_xticklabels(col_labels, rotation=35, ha="right",
                           fontsize=8, color=COLORS["text"])
        ax.set_yticks(range(len(names)))
        ax.set_yticklabels(names, fontsize=7, color=COLORS["text"])
        if do_annot:
            for i in range(len(students_sorted)):
                for j in range(len(metrics_keys)):
                    val = data_arr[i, j]
                    ax.text(j, i, f"{val:.0f}", ha="center", va="center",
                            fontsize=6, color="black" if 30 < val < 70 else "white")
        cbar = fig.colorbar(im, ax=ax, fraction=0.03)
        cbar.ax.yaxis.set_tick_params(color=COLORS["text"], labelsize=7)
        plt.setp(cbar.ax.yaxis.get_ticklabels(), color=COLORS["text"])

    ax.set_title("Mapa de Calor: Métricas por Alumno",
                 fontsize=11, fontweight="bold", color=COLORS["text"])
    fig.patch.set_facecolor(COLORS["bg"])
    fig.tight_layout()
    return fig


def chart_top_risk_bar(all_students: List[Dict], top_n: int = 10,
                        figsize=(5, 4)) -> Figure:
    """Barras horizontales de los alumnos con mayor riesgo."""
    high_risk   = [s for s in all_students if s.get("risk_level") == "alto"]
    medium_risk = [s for s in all_students if s.get("risk_level") == "medio"]
    target = (high_risk + medium_risk)[:top_n]

    fig, ax = plt.subplots(figsize=figsize)
    _apply_dark_style(fig, ax)

    if not target:
        ax.text(0.5, 0.5, "¡Sin alumnos en riesgo!", transform=ax.transAxes,
                ha="center", va="center", color=COLORS["bajo"],
                fontsize=13, fontweight="bold")
        ax.set_title("Alumnos en Mayor Riesgo", fontsize=11, fontweight="bold",
                     color=COLORS["text"])
        return fig

    names      = [s.get("fullname", "?")[:26] for s in reversed(target)]
    scores     = [s["metrics"].get("engagement_score", 0) for s in reversed(target)]
    bar_colors = [COLORS[s.get("risk_level", "bajo")] for s in reversed(target)]

    bars = ax.barh(names, scores, color=bar_colors, edgecolor="none",
                   alpha=0.88, height=0.65, zorder=2)

    for bar, val in zip(bars, scores):
        ax.text(val + 0.8, bar.get_y() + bar.get_height() / 2,
                f"{val:.0f}", va="center", color=COLORS["text"],
                fontsize=8.5, fontweight="bold")

    ax.set_xlim(0, 112)
    ax.set_xlabel("Índice de Engagement")
    ax.set_title(f"Alumnos en Mayor Riesgo (Top {len(target)})",
                 fontsize=11, fontweight="bold", color=COLORS["text"])
    # Línea de referencia
    ax.axvline(30, color=COLORS["alto"], linestyle=":", linewidth=1, alpha=0.5)
    ax.axvline(60, color=COLORS["bajo"], linestyle=":", linewidth=1, alpha=0.5)
    fig.tight_layout()
    return fig


# ============================================================
# Gráficas de detalle de alumno
# ============================================================

def chart_student_radar(metrics: Dict, figsize=(4.5, 4.5)) -> Figure:
    """
    Gráfica radar/araña. Doble capa de relleno para efecto glow suave.
    """
    categories = ["Engagement", "Completitud", "Entregas",
                  "A Tiempo", "Cuestion.", "Académico"]
    values = [
        metrics.get("engagement_score", 0),
        metrics.get("completion_rate",  0),
        metrics.get("submission_rate",  0),
        metrics.get("on_time_rate",     0),
        metrics.get("quiz_avg_pct")  if metrics.get("quiz_avg_pct")  is not None else 0,
        metrics.get("academic_score",  0),
    ]

    N      = len(categories)
    angles = [n / float(N) * 2 * np.pi for n in range(N)]
    angles += angles[:1]
    values_plot = values + values[:1]

    fig = Figure(figsize=figsize, facecolor=COLORS["bg"])
    ax  = fig.add_subplot(111, polar=True)
    ax.set_facecolor(COLORS["bg_card"])

    ax.spines["polar"].set_color(COLORS["grid"])
    ax.spines["polar"].set_linewidth(0.8)
    ax.tick_params(colors=COLORS["text"])
    ax.set_rlabel_position(30)
    ax.yaxis.set_tick_params(labelsize=6)
    ax.set_ylim(0, 100)
    ax.yaxis.set_major_locator(mticker.MultipleLocator(20))
    ax.grid(color=COLORS["grid"], linestyle="-", linewidth=0.4, alpha=0.5)

    # Relleno exterior (glow)
    ax.fill(angles, values_plot, color=COLORS["primary"], alpha=0.12)
    # Relleno interior más opaco
    ax.fill(angles, values_plot, color=COLORS["primary"], alpha=0.25)
    # Línea principal
    ax.plot(angles, values_plot, color=COLORS["primary"],
            linewidth=2.5, solid_capstyle="round")
    # Puntos en vértices
    ax.scatter(angles[:-1], values, color=COLORS["accent"],
               s=55, zorder=5, edgecolors=COLORS["bg"], linewidths=1)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(categories, size=8.5, color=COLORS["text"])

    fig.suptitle("Perfil del Alumno", color=COLORS["text"],
                 fontsize=11, fontweight="bold", y=0.98)
    fig.tight_layout()
    return fig


def chart_student_grade_timeline(metrics: Dict, figsize=(6, 3)) -> Figure:
    """
    Línea de tiempo de calificaciones con relleno degradado bajo la curva.
    """
    items = metrics.get("grade_items", [])
    dated = [
        (i["gradedate"], i["grade_pct"], i["name"])
        for i in items
        if i.get("gradedate") and i.get("grade_pct") is not None
    ]
    dated.sort(key=lambda x: x[0])

    fig, ax = plt.subplots(figsize=figsize)
    _apply_dark_style(fig, ax)

    if not dated:
        ax.text(0.5, 0.5, "Sin calificaciones registradas",
                transform=ax.transAxes, ha="center", va="center",
                color=COLORS["text"], fontsize=10)
        ax.set_title("Evolución de Calificaciones", fontsize=11, fontweight="bold",
                     color=COLORS["text"])
        return fig

    dates  = [datetime.fromtimestamp(d[0]) for d in dated]
    grades = [d[1] for d in dated]
    names  = [d[2] for d in dated]

    # Zona aprobado
    ax.axhspan(50, 100, alpha=0.04, color=COLORS["bajo"])
    ax.axhline(50, color=COLORS["medio"], linestyle="--",
               linewidth=1.2, alpha=0.65, label="Aprobado (50%)")

    # Relleno degradado bajo la línea
    ax.fill_between(dates, grades, 0, alpha=0.15, color=COLORS["primary"], zorder=1)
    ax.fill_between(dates, grades, 0, alpha=0.07, color=COLORS["primary"], zorder=1)

    # Línea principal
    ax.plot(dates, grades, color=COLORS["primary"], linewidth=2.5,
            marker="o", markersize=7, markerfacecolor=COLORS["accent"],
            markeredgecolor=COLORS["bg"], markeredgewidth=1.2, zorder=3)

    # Anotaciones
    for date, grade, name in zip(dates, grades, names):
        ax.annotate(
            f"{grade:.0f}%", (date, grade),
            textcoords="offset points", xytext=(0, 9),
            ha="center", fontsize=7.5, color=COLORS["text"], alpha=0.9,
        )

    # Tendencia
    if len(grades) >= 3:
        x_num = np.array(range(len(grades)))
        z = np.polyfit(x_num, grades, 1)
        p = np.poly1d(z)
        ax.plot(dates, p(x_num), color=COLORS["secondary"], linestyle=":",
                linewidth=1.8, alpha=0.75, label="Tendencia")

    ax.set_ylim(0, 112)
    ax.set_ylabel("Calificación (%)")
    ax.set_title("Evolución de Calificaciones", fontsize=11, fontweight="bold",
                 color=COLORS["text"])
    ax.legend(facecolor=COLORS["bg_card"], labelcolor=COLORS["text"], fontsize=8)
    fig.autofmt_xdate()
    fig.tight_layout()
    return fig


def chart_student_activity_bars(metrics: Dict, figsize=(5, 3.5)) -> Figure:
    """Barras de métricas del alumno con colores semafóricos."""
    labels = ["Engagement", "Completitud", "Entregas", "A Tiempo"]
    student_vals = [
        metrics.get("engagement_score", 0),
        metrics.get("completion_rate",  0),
        metrics.get("submission_rate",  0),
        metrics.get("on_time_rate",     0),
    ]

    fig, ax = plt.subplots(figsize=figsize)
    _apply_dark_style(fig, ax)

    x = np.arange(len(labels))
    bar_colors = [
        COLORS["bajo"] if v >= 70 else (COLORS["medio"] if v >= 45 else COLORS["alto"])
        for v in student_vals
    ]

    bars = ax.bar(x, student_vals, color=bar_colors, edgecolor="none",
                  alpha=0.88, width=0.6, zorder=2)

    for bar, val in zip(bars, student_vals):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 1.2,
            f"{val:.0f}%",
            ha="center", va="bottom",
            color=COLORS["text"], fontsize=9.5, fontweight="bold",
        )

    ax.axhline(70, color=COLORS["neutral"], linestyle="--",
               linewidth=1, alpha=0.5, label="70%")
    ax.set_ylim(0, 118)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, color=COLORS["text"])
    ax.set_ylabel("Porcentaje (%)")
    ax.set_title("Indicadores de Actividad", fontsize=11, fontweight="bold",
                 color=COLORS["text"])
    ax.legend(facecolor=COLORS["bg_card"], labelcolor=COLORS["text"], fontsize=8)
    fig.tight_layout()
    return fig


def chart_student_quiz_history(attempts: List[Dict], quizzes: List[Dict],
                                figsize=(5, 3)) -> Figure:
    """Barras de resultados de cuestionarios."""
    fig, ax = plt.subplots(figsize=figsize)
    _apply_dark_style(fig, ax)

    if not attempts:
        ax.text(0.5, 0.5, "Sin intentos de cuestionario",
                transform=ax.transAxes, ha="center", va="center",
                color=COLORS["text"], fontsize=10)
        ax.set_title("Cuestionarios", fontsize=11, fontweight="bold",
                     color=COLORS["text"])
        return fig

    quiz_map = {q["id"]: q for q in quizzes}
    points   = []
    for att in attempts:
        state = att.get("state", "")
        if state not in ("finished", "gradedright", "gradedwrong", "gradedpartial"):
            continue
        grade = att.get("grade")
        if grade is None:
            continue
        quiz  = quiz_map.get(att.get("quizid"), {})
        max_g = float(quiz.get("grade", 10) or 10)
        pct   = (float(grade) / max_g) * 100 if max_g > 0 else 0
        name  = quiz.get("name", f"Quiz {att.get('quizid')}")[:18]
        ts    = att.get("timefinish", 0)
        points.append((ts, pct, name))

    points.sort(key=lambda x: x[0])

    if not points:
        ax.text(0.5, 0.5, "Sin intentos completados",
                transform=ax.transAxes, ha="center", va="center",
                color=COLORS["text"], fontsize=10)
        ax.set_title("Cuestionarios", fontsize=11, fontweight="bold",
                     color=COLORS["text"])
        return fig

    x_pos = range(len(points))
    pctes  = [p[1] for p in points]
    names  = [p[2] for p in points]
    colors = [COLORS["bajo"] if p >= 50 else COLORS["alto"] for p in pctes]

    bars = ax.bar(x_pos, pctes, color=colors, edgecolor="none",
                  alpha=0.88, zorder=2)
    for bar, val in zip(bars, pctes):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1.2,
                f"{val:.0f}%", ha="center", va="bottom",
                color=COLORS["text"], fontsize=8.5)

    ax.axhline(50, color=COLORS["medio"], linestyle="--",
               linewidth=1.2, alpha=0.7, label="Aprobado (50%)")
    ax.set_ylim(0, 118)
    ax.set_xticks(x_pos)
    ax.set_xticklabels(names, rotation=30, ha="right",
                       fontsize=7, color=COLORS["text"])
    ax.set_ylabel("Puntuación (%)")
    ax.set_title("Resultados de Cuestionarios", fontsize=11, fontweight="bold",
                 color=COLORS["text"])
    ax.legend(facecolor=COLORS["bg_card"], labelcolor=COLORS["text"], fontsize=8)
    fig.tight_layout()
    return fig


def chart_student_submissions_timeline(
    submissions: List[Dict], assignments: List[Dict], figsize=(9, 5)
) -> Figure:
    """
    Línea de tiempo de entregas vs fechas límite.
    Muestra TODAS las tareas del curso.
    Verde=a tiempo  |  Rojo=tarde/sin entregar  |  Naranja=borrador.
    """
    if not assignments:
        fig, ax = plt.subplots(figsize=figsize)
        _apply_dark_style(fig, ax)
        ax.text(0.5, 0.5, "Sin tareas en el curso",
                transform=ax.transAxes, ha="center", va="center",
                color=COLORS["text"], fontsize=10)
        ax.set_title("Historial de Entregas", fontsize=11, fontweight="bold",
                     color=COLORS["text"])
        return fig

    n     = len(assignments)
    fig_h = max(figsize[1], n * 0.45 + 1.5)
    fig, ax = plt.subplots(figsize=(figsize[0], fig_h))
    _apply_dark_style(fig, ax)

    sub_map = {s["assignid"]: s for s in submissions}
    now     = datetime.now()

    for i, assign in enumerate(assignments):
        aid    = assign.get("id")
        due    = assign.get("duedate", 0)
        sub    = sub_map.get(aid)
        status = sub.get("status", "") if sub else ""
        y      = i

        if due:
            due_dt = datetime.fromtimestamp(due)
            ax.scatter(due_dt, y, color=COLORS["neutral"], marker="|",
                       s=220, linewidths=2, zorder=3)

        if status == "submitted":
            sub_ts = sub.get("timemodified", 0) or sub.get("timecreated", 0)
            if sub_ts:
                sub_dt = datetime.fromtimestamp(sub_ts)
                color  = COLORS["bajo"] if (not due or sub_ts <= due) else COLORS["alto"]
                ax.scatter(sub_dt, y, color=color, marker="o",
                           s=90, zorder=4, edgecolors=COLORS["bg"], linewidths=0.8)
                if due:
                    due_dt2 = datetime.fromtimestamp(due)
                    ax.hlines(y, min(sub_dt, due_dt2), max(sub_dt, due_dt2),
                              color=color, linewidth=1.5, alpha=0.4)
            else:
                if due:
                    ax.scatter(datetime.fromtimestamp(due), y,
                               color=COLORS["bajo"], marker="o",
                               s=90, zorder=4)

        elif status in ("draft", "new"):
            sub_ts = sub.get("timemodified", 0) or sub.get("timecreated", 0)
            ref = datetime.fromtimestamp(sub_ts) if sub_ts else (
                datetime.fromtimestamp(due) if due else now
            )
            ax.scatter(ref, y, color=COLORS["medio"], marker="D",
                       s=65, zorder=4)
        else:
            if due and datetime.fromtimestamp(due) < now:
                ax.scatter(now, y, color=COLORS["alto"], marker="x",
                           s=90, zorder=4, linewidths=2.2)

    ax.set_yticks(range(n))
    ax.set_yticklabels(
        [a.get("name", f"Tarea {i+1}")[:28] for i, a in enumerate(assignments)],
        fontsize=7, color=COLORS["text"],
    )

    legend_items = [
        mpatches.Patch(color=COLORS["bajo"],    label="Entregado a tiempo"),
        mpatches.Patch(color=COLORS["alto"],    label="Tarde / No entregado"),
        mpatches.Patch(color=COLORS["medio"],   label="Borrador (sin enviar)"),
        mpatches.Patch(color=COLORS["neutral"], label="Fecha límite"),
    ]
    ax.legend(handles=legend_items, facecolor=COLORS["bg_card"],
              labelcolor=COLORS["text"], fontsize=7, loc="lower right")
    ax.set_title("Historial de Entregas", fontsize=11, fontweight="bold",
                 color=COLORS["text"])
    fig.autofmt_xdate()
    fig.tight_layout()
    return fig


def chart_prediction_gauge(prediction: Dict, metrics: Dict,
                            figsize=(5, 3.2)) -> Figure:
    """
    Indicadores semicirculares (half-donut) para nota predicha y riesgo.
    Mucho más visual que las barras horizontales anteriores.
    """
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=figsize)
    fig.patch.set_facecolor(COLORS["bg"])
    for ax in (ax1, ax2):
        ax.set_facecolor(COLORS["bg"])

    pred_pct  = float(prediction.get("predicted_grade_pct", 0))
    max_g     = float(metrics.get("course_total_max") or 10.0)
    pred_grade= float(prediction.get("predicted_grade", 0))
    risk_pct  = float(prediction.get("risk_probability", 0)) * 100

    grade_color = COLORS["bajo"] if pred_pct >= 50 else COLORS["alto"]
    risk_color  = (
        COLORS["alto"]  if risk_pct > 60 else
        COLORS["medio"] if risk_pct > 30 else
        COLORS["bajo"]
    )

    _draw_semicircle_gauge(ax1, pred_pct,  grade_color,
                           "Nota Estimada",
                           sublabel=f"{pred_grade:.1f} / {max_g:.0f}")
    _draw_semicircle_gauge(ax2, risk_pct, risk_color,
                           "Riesgo de Suspenso")

    method = prediction.get("method", "heuristic")
    fig.text(0.5, 0.01,
             f"Método: {'Machine Learning (GBT)' if method == 'ml' else 'Heurístico'}",
             ha="center", fontsize=7, color=COLORS["fg_dim"])
    fig.tight_layout(rect=[0, 0.04, 1, 1])
    return fig


def chart_student_activity_heatmap_week(
    timestamps: List[int], figsize=(5, 3.5)
) -> Figure:
    """
    Mapa de calor día de semana × hora del día.
    Usa seaborn.heatmap si disponible.
    """
    DAYS = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
    matrix = np.zeros((7, 24), dtype=int)

    for ts in timestamps:
        try:
            dt = datetime.fromtimestamp(ts)
            matrix[dt.weekday(), dt.hour] += 1
        except (OSError, ValueError, OverflowError):
            pass

    fig, ax = plt.subplots(figsize=figsize)

    if not timestamps or matrix.max() == 0:
        _apply_dark_style(fig, ax)
        ax.text(0.5, 0.5, "Sin registros de actividad disponibles",
                transform=ax.transAxes, ha="center", va="center",
                color=COLORS["text"], fontsize=10)
        ax.set_title("Patrón Horario de Actividad", fontsize=11, fontweight="bold",
                     color=COLORS["text"])
        return fig

    hour_labels = [str(h) if h % 3 == 0 else "" for h in range(24)]

    if _HAS_SEABORN:
        fig.patch.set_facecolor(COLORS["bg"])
        ax.set_facecolor(COLORS["bg_card"])
        sns.heatmap(
            matrix,
            xticklabels=hour_labels,
            yticklabels=DAYS,
            cmap="YlOrRd",
            vmin=0, vmax=max(1, matrix.max()),
            linewidths=0.3,
            linecolor=COLORS["bg"],
            ax=ax,
            cbar_kws={"shrink": 0.75, "aspect": 28},
        )
        ax.set_facecolor(COLORS["bg_card"])
        ax.tick_params(colors=COLORS["text"], labelsize=7.5, length=0)
        ax.set_xticklabels(ax.get_xticklabels(), color=COLORS["text"])
        ax.set_yticklabels(ax.get_yticklabels(), color=COLORS["text"], rotation=0)
        _style_seaborn_colorbar(ax)
    else:
        _apply_dark_style(fig, ax)
        im = ax.imshow(matrix, cmap="YlOrRd", aspect="auto",
                       vmin=0, vmax=max(1, matrix.max()))
        ax.set_yticks(range(7))
        ax.set_yticklabels(DAYS, fontsize=8, color=COLORS["text"])
        ax.set_xticks(range(0, 24, 3))
        ax.set_xticklabels([f"{h:02d}h" for h in range(0, 24, 3)],
                           fontsize=7, color=COLORS["text"])
        cbar = fig.colorbar(im, ax=ax, fraction=0.03, pad=0.02)
        plt.setp(cbar.ax.yaxis.get_ticklabels(), color=COLORS["text"], fontsize=7)

    # Anotar el pico de actividad
    max_idx = np.unravel_index(matrix.argmax(), matrix.shape)
    DAYS_FULL = ["Lunes", "Martes", "Miércoles", "Jueves",
                 "Viernes", "Sábado", "Domingo"]
    ax.set_xlabel(
        f"Pico: {DAYS_FULL[max_idx[0]]} a las {max_idx[1]:02d}h",
        fontsize=8, color=COLORS["accent"],
    )
    ax.set_title("Patrón Horario de Actividad", fontsize=11, fontweight="bold",
                 color=COLORS["text"])
    fig.patch.set_facecolor(COLORS["bg"])
    fig.tight_layout()
    return fig


def chart_student_weekly_activity(
    timestamps: List[int],
    session_count: Optional[int] = None,
    avg_session_min: Optional[float] = None,
    weeks_active: Optional[int] = None,
    figsize=(5, 3.5),
) -> Figure:
    """
    Histograma de actividad semanal con caja de estadísticas de sesiones.
    """
    fig, ax = plt.subplots(figsize=figsize)
    _apply_dark_style(fig, ax)

    if not timestamps:
        ax.text(0.5, 0.5, "Sin datos de actividad",
                transform=ax.transAxes, ha="center", va="center",
                color=COLORS["text"], fontsize=10)
        ax.set_title("Actividad Semanal", fontsize=11, fontweight="bold",
                     color=COLORS["text"])
        return fig

    week_counts: Dict[str, int] = {}
    week_dates:  Dict[str, datetime] = {}
    for ts in timestamps:
        try:
            dt     = datetime.fromtimestamp(ts)
            monday = dt - timedelta(days=dt.weekday())
            key    = monday.strftime("%Y-%W")
            week_counts[key] = week_counts.get(key, 0) + 1
            if key not in week_dates:
                week_dates[key] = monday
        except (OSError, ValueError, OverflowError):
            pass

    if not week_counts:
        ax.text(0.5, 0.5, "Sin datos de actividad",
                transform=ax.transAxes, ha="center", va="center",
                color=COLORS["text"], fontsize=10)
        ax.set_title("Actividad Semanal", fontsize=11, fontweight="bold",
                     color=COLORS["text"])
        return fig

    sorted_keys = sorted(week_dates.keys())
    labels  = [week_dates[k].strftime("%d/%m") for k in sorted_keys]
    counts  = [week_counts[k] for k in sorted_keys]
    max_c   = max(counts) if counts else 1

    bar_colors = [
        COLORS["bajo"]  if c >= max_c * 0.65 else
        COLORS["medio"] if c >= max_c * 0.30 else
        COLORS["alto"]
        for c in counts
    ]

    x = range(len(labels))
    ax.bar(x, counts, color=bar_colors, edgecolor="none", alpha=0.88, zorder=2)

    # KDE semanal suave si hay suficientes semanas
    if len(counts) >= 4:
        x_k, y_k = _kde_line(
            [i for i, c in enumerate(counts) for _ in range(c)],
            x_min=-0.5, x_max=len(counts) - 0.5, bandwidth=1.2
        )
        if len(x_k):
            scale = len(counts) * max_c * 0.35
            ax.plot(x_k, y_k * scale, color=COLORS["text"],
                    linewidth=1.8, alpha=0.5, zorder=4)

    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=45, ha="right",
                       fontsize=7, color=COLORS["text"])
    ax.set_ylabel("Eventos registrados", fontsize=8)
    ax.set_title("Actividad Semanal", fontsize=11, fontweight="bold",
                 color=COLORS["text"])

    # Caja de estadísticas de sesiones
    info_parts: List[str] = []
    if session_count is not None:
        info_parts.append(f"Sesiones: {session_count}")
    if avg_session_min is not None:
        info_parts.append(f"Duración media: {avg_session_min:.0f} min")
    if weeks_active is not None:
        info_parts.append(f"Semanas activas: {weeks_active}")
    if info_parts:
        ax.text(0.02, 0.97, "\n".join(info_parts),
                transform=ax.transAxes, ha="left", va="top",
                fontsize=7.5, color=COLORS["accent"],
                bbox=dict(facecolor=COLORS["bg_card"], alpha=0.88,
                          edgecolor=COLORS["border"], boxstyle="round,pad=0.4"))
    else:
        ax.text(0.5, 0.02,
                "Logs no disponibles — datos desde entregas, quizzes y foros",
                transform=ax.transAxes, ha="center", fontsize=7,
                color=COLORS["fg_dim"], style="italic")

    fig.tight_layout()
    return fig


def chart_submission_advance_bars(
    submissions: List[Dict], assignments: List[Dict], figsize=(5, 4)
) -> Figure:
    """
    Barras horizontales: verde=entregó antes del plazo, rojo=tarde/no entregó.
    """
    fig, ax = plt.subplots(figsize=figsize)
    _apply_dark_style(fig, ax)

    if not assignments:
        ax.text(0.5, 0.5, "Sin tareas en el curso",
                transform=ax.transAxes, ha="center", va="center",
                color=COLORS["text"], fontsize=10)
        ax.set_title("Antelación en Entregas", fontsize=11, fontweight="bold",
                     color=COLORS["text"])
        return fig

    sub_map = {s["assignid"]: s for s in submissions}
    now     = datetime.now()

    names:    List[str]   = []
    advances: List[float] = []
    bar_cols: List[str]   = []

    for assign in assignments:
        aid  = assign.get("id")
        due  = assign.get("duedate", 0)
        if not due:
            continue
        name   = assign.get("name", "Tarea")[:24]
        sub    = sub_map.get(aid)
        status = sub.get("status", "submitted") if sub else ""

        if sub and status not in ("new", "draft", "reopened"):
            ts = sub.get("timemodified", 0) or sub.get("timecreated", 0)
            if ts:
                advance = (due - ts) / 86400.0
                names.append(name)
                advances.append(advance)
                bar_cols.append(COLORS["bajo"] if advance >= 0 else COLORS["alto"])
        elif datetime.fromtimestamp(due) < now:
            names.append(f"✗ {name}")
            advances.append(-7.0)
            bar_cols.append(COLORS["alto"])

    if not names:
        ax.text(0.5, 0.5, "Sin tareas con fecha límite registradas",
                transform=ax.transAxes, ha="center", va="center",
                color=COLORS["text"], fontsize=9)
        ax.set_title("Antelación en Entregas", fontsize=11, fontweight="bold",
                     color=COLORS["text"])
        return fig

    y = list(range(len(names)))
    ax.barh(y, advances, color=bar_cols, edgecolor="none", alpha=0.88, zorder=2)
    ax.axvline(0, color=COLORS["neutral"], linewidth=1.8,
               linestyle="--", alpha=0.7)

    for yi, val, name in zip(y, advances, names):
        if "✗" in name:
            ax.text(0.3, yi, "No entregada", va="center", ha="left",
                    color=COLORS["alto"], fontsize=7)
        else:
            lbl = f"+{val:.1f}d" if val >= 0 else f"{val:.1f}d"
            ha  = "left" if val >= 0 else "right"
            x_off = val + 0.2 if val >= 0 else val - 0.2
            ax.text(x_off, yi, lbl, va="center", ha=ha,
                    color=COLORS["text"], fontsize=7)

    ax.set_yticks(y)
    ax.set_yticklabels(names, fontsize=7, color=COLORS["text"])
    ax.set_xlabel("Días respecto al plazo  (+ = entregó antes)",
                  fontsize=8, color=COLORS["text"])
    ax.set_title("Antelación en Entregas", fontsize=11, fontweight="bold",
                 color=COLORS["text"])
    fig.tight_layout()
    return fig


def chart_correlation_matrix(all_students: List[Dict], figsize=(5, 4)) -> Figure:
    """
    Matriz de correlación entre métricas.
    Usa seaborn.heatmap si disponible (mucho más bonita con anotaciones).
    """
    keys = [
        ("engagement_score", "Engagement"),
        ("completion_rate",  "Completitud"),
        ("submission_rate",  "Entregas"),
        ("quiz_avg_pct",     "Cuestion."),
        ("forum_posts_count","Foros"),
        ("final_grade_pct",  "Nota"),
    ]

    fig, ax = plt.subplots(figsize=figsize)

    data_cols, labels = [], []
    for key, label in keys:
        col = [s["metrics"].get(key) for s in all_students
               if s.get("metrics", {}).get(key) is not None]
        if len(col) >= 3:
            data_cols.append(col[:len(all_students)])
            labels.append(label)

    if len(data_cols) < 2:
        _apply_dark_style(fig, ax)
        ax.text(0.5, 0.5, "Insuficientes datos para\ncalcular correlaciones",
                transform=ax.transAxes, ha="center", va="center",
                color=COLORS["text"], fontsize=10)
        ax.set_title("Correlación entre Métricas", fontsize=11, fontweight="bold",
                     color=COLORS["text"])
        return fig

    min_len     = min(len(c) for c in data_cols)
    matrix_data = np.array([c[:min_len] for c in data_cols], dtype=float)

    # Descartar columnas con desviación estándar = 0 (valores constantes)
    # para evitar división por cero en np.corrcoef
    stds        = matrix_data.std(axis=1)
    valid_mask  = stds > 1e-9
    if valid_mask.sum() < 2:
        _apply_dark_style(fig, ax)
        ax.text(0.5, 0.5, "Métricas sin variación suficiente",
                transform=ax.transAxes, ha="center", va="center",
                color=COLORS["text"], fontsize=10)
        ax.set_title("Correlación entre Métricas", fontsize=11, fontweight="bold",
                     color=COLORS["text"])
        return fig
    matrix_data = matrix_data[valid_mask]
    labels      = [lbl for lbl, ok in zip(labels, valid_mask) if ok]

    corr_matrix = np.corrcoef(matrix_data)
    # Reemplazar NaN residuales (si los hubiera) por 0
    corr_matrix = np.nan_to_num(corr_matrix, nan=0.0)

    if _HAS_SEABORN:
        fig.patch.set_facecolor(COLORS["bg"])
        ax.set_facecolor(COLORS["bg_card"])
        sns.heatmap(
            corr_matrix,
            xticklabels=labels,
            yticklabels=labels,
            cmap="RdYlGn",
            vmin=-1, vmax=1,
            annot=False,   # anotaciones manuales para control de color
            linewidths=0.4,
            linecolor=COLORS["bg"],
            ax=ax,
            cbar_kws={"shrink": 0.75, "aspect": 28},
        )
        ax.set_facecolor(COLORS["bg_card"])
        ax.tick_params(colors=COLORS["text"], labelsize=8, length=0)
        ax.set_xticklabels(ax.get_xticklabels(), rotation=35, ha="right",
                           color=COLORS["text"], fontsize=8)
        ax.set_yticklabels(ax.get_yticklabels(), color=COLORS["text"],
                           fontsize=8, rotation=0)
        _style_seaborn_colorbar(ax)
        # Anotaciones manuales con color según contraste
        for i in range(len(labels)):
            for j in range(len(labels)):
                val = corr_matrix[i, j]
                tc  = "black" if -0.25 < val < 0.25 else "white"
                ax.text(j + 0.5, i + 0.5, f"{val:.2f}",
                        ha="center", va="center",
                        fontsize=7.5, color=tc, fontweight="bold")
    else:
        _apply_dark_style(fig, ax)
        im = ax.imshow(corr_matrix, cmap="RdYlGn", vmin=-1, vmax=1)
        ax.set_xticks(range(len(labels)))
        ax.set_yticks(range(len(labels)))
        ax.set_xticklabels(labels, rotation=35, ha="right",
                           fontsize=8, color=COLORS["text"])
        ax.set_yticklabels(labels, fontsize=8, color=COLORS["text"])
        for i in range(len(labels)):
            for j in range(len(labels)):
                val = corr_matrix[i, j]
                tc  = "black" if -0.3 < val < 0.3 else "white"
                ax.text(j, i, f"{val:.2f}", ha="center", va="center",
                        fontsize=7, color=tc)
        cbar = fig.colorbar(im, ax=ax, fraction=0.04)
        plt.setp(cbar.ax.yaxis.get_ticklabels(), color=COLORS["text"], fontsize=7)

    ax.set_title("Correlación entre Métricas", fontsize=11, fontweight="bold",
                 color=COLORS["text"])
    fig.patch.set_facecolor(COLORS["bg"])
    fig.tight_layout()
    return fig


# ============================================================
# Nuevas gráficas de análisis de curso
# ============================================================

def chart_course_funnel(all_students: List[Dict], figsize=(7, 4)) -> Figure:
    """
    Funnel horizontal de progresión del curso.
    Muestra cuántos alumnos superan cada etapa: matrícula → acceso
    → primera entrega → completitud >50% → sin riesgo alto.
    """
    fig, ax = plt.subplots(figsize=figsize)
    _apply_dark_style(fig, ax)

    n = len(all_students)
    if n == 0:
        ax.text(0.5, 0.5, "Sin datos de alumnos", transform=ax.transAxes,
                ha="center", va="center", color=COLORS["text"], fontsize=10)
        ax.set_title("Progresión del Curso", fontsize=11, fontweight="bold",
                     color=COLORS["text"])
        return fig

    stages = [
        ("Matriculados",
         n,
         COLORS["primary"]),
        ("Accedieron",
         sum(1 for s in all_students if s.get("lastaccess", 0) > 0),
         COLORS["accent"]),
        ("Entregaron algo",
         sum(1 for s in all_students
             if s.get("metrics", {}).get("submitted_assignments", 0) > 0),
         COLORS["bajo"]),
        ("Completitud >50 %",
         sum(1 for s in all_students
             if s.get("metrics", {}).get("completion_rate", 0) > 50),
         COLORS["accent2"]),
        ("Sin riesgo alto",
         sum(1 for s in all_students if s.get("risk_level") != "alto"),
         COLORS["bajo"]),
    ]

    labels = [s[0] for s in stages]
    values = [s[1] for s in stages]
    colors = [s[2] for s in stages]

    y_pos = range(len(labels))
    bars  = ax.barh(y_pos, values, color=colors, edgecolor="none",
                    alpha=0.88, height=0.55, zorder=2)

    for bar, val in zip(bars, values):
        pct = val / n * 100 if n > 0 else 0
        ax.text(
            val + n * 0.01,
            bar.get_y() + bar.get_height() / 2,
            f"{val}  ({pct:.0f}%)",
            va="center", color=COLORS["text"], fontsize=9, fontweight="bold",
        )

    # Caída entre etapas
    for i in range(1, len(values)):
        drop = values[i - 1] - values[i]
        if drop > 0:
            ax.text(
                values[i] / 2,
                i - 0.5,
                f"−{drop}",
                ha="center", va="center",
                color=COLORS["fg_dim"], fontsize=7.5, style="italic",
            )

    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels, color=COLORS["text"], fontsize=9)
    ax.set_xlabel("N.º Alumnos")
    ax.set_xlim(0, n * 1.38)
    ax.set_title("Funnel de Progresión del Curso",
                 fontsize=11, fontweight="bold", color=COLORS["text"])
    ax.invert_yaxis()
    fig.tight_layout()
    return fig


def chart_submissions_heatmap(all_students: List[Dict], assignments: List[Dict],
                               figsize=(10, 6)) -> Figure:
    """
    Heatmap alumnos × tareas.
    Verde=a tiempo  |  Naranja=tarde/borrador  |  Rojo=sin entregar  |  Gris=pendiente.
    Alumnos ordenados por engagement (mejor arriba). Tareas por fecha límite.
    """
    from matplotlib.colors import LinearSegmentedColormap

    if not all_students or not assignments:
        fig, ax = plt.subplots(figsize=figsize)
        _apply_dark_style(fig, ax)
        ax.text(0.5, 0.5, "Sin datos de tareas", transform=ax.transAxes,
                ha="center", va="center", color=COLORS["text"], fontsize=10)
        ax.set_title("Mapa de Entregas", fontsize=11, fontweight="bold",
                     color=COLORS["text"])
        return fig

    sorted_assigns = sorted(
        assignments,
        key=lambda a: (a.get("duedate") or 9_999_999_999),
    )
    sorted_students = sorted(
        all_students,
        key=lambda s: s.get("metrics", {}).get("engagement_score", 0),
        reverse=True,
    )

    assign_labels  = [a.get("name", "?")[:16] for a in sorted_assigns]
    student_labels = [s.get("fullname", "?")[:22] for s in sorted_students]

    now    = datetime.now().timestamp()
    matrix = np.full((len(sorted_students), len(sorted_assigns)), -1.0)

    for i, student in enumerate(sorted_students):
        sub_map = {sub["assignid"]: sub for sub in student.get("submissions", [])}
        for j, assign in enumerate(sorted_assigns):
            aid    = assign.get("id")
            due    = assign.get("duedate", 0)
            sub    = sub_map.get(aid)
            status = sub.get("status", "") if sub else ""

            if status == "submitted":
                ts = sub.get("timemodified", 0) or sub.get("timecreated", 0)
                matrix[i, j] = 2.0 if (not due or ts <= due) else 1.0
            elif status in ("draft", "new"):
                matrix[i, j] = 1.0
            elif due and due < now:
                matrix[i, j] = 0.0
            # else -1: pendiente, no vencido

    cmap_sub  = LinearSegmentedColormap.from_list(
        "sub3", [COLORS["alto"], COLORS["medio"], COLORS["bajo"]], N=256)
    mask_pend = matrix < 0
    disp      = np.where(mask_pend, np.nan, matrix)

    fig, ax = plt.subplots(figsize=figsize)

    if _HAS_SEABORN:
        fig.patch.set_facecolor(COLORS["bg"])
        ax.set_facecolor(COLORS["bg_card"])
        sns.heatmap(
            disp,
            xticklabels=assign_labels,
            yticklabels=student_labels,
            cmap=cmap_sub,
            vmin=0, vmax=2,
            mask=mask_pend,
            linewidths=0.25,
            linecolor=COLORS["bg"],
            ax=ax,
            cbar=False,
        )
        for i in range(len(sorted_students)):
            for j in range(len(sorted_assigns)):
                if mask_pend[i, j]:
                    ax.add_patch(plt.Rectangle(
                        (j, i), 1, 1,
                        fill=True, facecolor=COLORS["grid"],
                        edgecolor=COLORS["bg"], linewidth=0.25,
                    ))
        ax.set_facecolor(COLORS["bg_card"])
        ax.tick_params(colors=COLORS["text"], labelsize=7, length=0)
        ax.set_xticklabels(ax.get_xticklabels(), rotation=35, ha="right",
                           color=COLORS["text"], fontsize=7)
        ax.set_yticklabels(ax.get_yticklabels(), color=COLORS["text"], fontsize=7)
    else:
        _apply_dark_style(fig, ax)
        ax.imshow(disp, cmap=cmap_sub, aspect="auto", vmin=0, vmax=2)
        ax.set_xticks(range(len(assign_labels)))
        ax.set_xticklabels(assign_labels, rotation=35, ha="right",
                           fontsize=7, color=COLORS["text"])
        ax.set_yticks(range(len(student_labels)))
        ax.set_yticklabels(student_labels, fontsize=7, color=COLORS["text"])

    legend_items = [
        mpatches.Patch(color=COLORS["bajo"],   label="A tiempo"),
        mpatches.Patch(color=COLORS["medio"],  label="Tarde / borrador"),
        mpatches.Patch(color=COLORS["alto"],   label="No entregado"),
        mpatches.Patch(color=COLORS["grid"],   label="Pendiente"),
    ]
    ax.legend(handles=legend_items, loc="lower right", fontsize=7,
              facecolor=COLORS["bg_card"], labelcolor=COLORS["text"],
              framealpha=0.9, bbox_to_anchor=(1.0, -0.18))

    ax.set_title("Mapa de Entregas  (Alumnos × Tareas)",
                 fontsize=11, fontweight="bold", color=COLORS["text"])
    fig.patch.set_facecolor(COLORS["bg"])
    fig.tight_layout()
    return fig


def chart_top_bottom_comparison(all_students: List[Dict],
                                 figsize=(8, 4.5)) -> Figure:
    """
    Comparación Top 25% vs Bottom 25% por nota académica.
    5 métricas clave para identificar qué diferencia a los mejores alumnos.
    """
    fig, ax = plt.subplots(figsize=figsize)
    _apply_dark_style(fig, ax)

    if len(all_students) < 4:
        ax.text(0.5, 0.5, "Se necesitan al menos 4 alumnos",
                transform=ax.transAxes, ha="center", va="center",
                color=COLORS["text"], fontsize=10)
        ax.set_title("Top 25% vs Bottom 25%", fontsize=11, fontweight="bold",
                     color=COLORS["text"])
        return fig

    sorted_s = sorted(
        all_students,
        key=lambda s: (s.get("metrics", {}).get("academic_score") or
                       s.get("metrics", {}).get("engagement_score", 0)),
        reverse=True,
    )
    group_n = max(1, len(sorted_s) // 4)
    top    = sorted_s[:group_n]
    bottom = sorted_s[-group_n:]

    metric_specs = [
        ("engagement_score", "Engagement"),
        ("completion_rate",  "Completitud"),
        ("submission_rate",  "Entregas"),
        ("on_time_rate",     "A Tiempo"),
        ("quiz_avg_pct",     "Cuestion."),
    ]

    def _avg(group, key):
        vals = [s.get("metrics", {}).get(key) or 0 for s in group]
        return float(np.mean(vals)) if vals else 0.0

    top_vals    = [_avg(top,    k) for k, _ in metric_specs]
    bottom_vals = [_avg(bottom, k) for k, _ in metric_specs]
    labels      = [lbl for _, lbl in metric_specs]

    x = np.arange(len(labels))
    w = 0.38

    bars1 = ax.bar(x - w / 2, top_vals,    w, color=COLORS["bajo"],
                   edgecolor="none", alpha=0.88,
                   label=f"Top {group_n}  (mejor nota)")
    bars2 = ax.bar(x + w / 2, bottom_vals, w, color=COLORS["alto"],
                   edgecolor="none", alpha=0.88,
                   label=f"Bottom {group_n}  (peor nota)")

    for bar, val in zip(list(bars1) + list(bars2), top_vals + bottom_vals):
        ax.text(bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 1.5,
                f"{val:.0f}",
                ha="center", va="bottom",
                color=COLORS["text"], fontsize=8)

    ax.set_xticks(x)
    ax.set_xticklabels(labels, color=COLORS["text"])
    ax.set_ylim(0, 120)
    ax.set_ylabel("Valor promedio (%)")
    ax.set_title("Top 25 % vs Bottom 25 % — ¿Qué hacen diferente?",
                 fontsize=11, fontweight="bold", color=COLORS["text"])
    ax.legend(facecolor=COLORS["bg_card"], labelcolor=COLORS["text"],
              fontsize=8, framealpha=0.9)
    fig.tight_layout()
    return fig


def chart_quiz_difficulty(all_students: List[Dict], quizzes: List[Dict],
                           figsize=(8, 4.5)) -> Figure:
    """
    Análisis de dificultad por cuestionario.
    Nota media (%) y tasa de aprobados, ordenados del más difícil al más fácil.
    """
    fig, ax = plt.subplots(figsize=figsize)
    _apply_dark_style(fig, ax)

    if not quizzes:
        ax.text(0.5, 0.5, "Sin cuestionarios en el curso",
                transform=ax.transAxes, ha="center", va="center",
                color=COLORS["text"], fontsize=10)
        ax.set_title("Dificultad de Cuestionarios", fontsize=11, fontweight="bold",
                     color=COLORS["text"])
        return fig

    quiz_map = {q["id"]: q for q in quizzes}
    stats: Dict[int, Any] = {}

    for student in all_students:
        for att in student.get("quiz_attempts", []):
            qid   = att.get("quizid")
            state = att.get("state", "")
            if state not in ("finished", "gradedright", "gradedwrong", "gradedpartial"):
                continue
            grade = att.get("grade")
            quiz  = quiz_map.get(qid, {})
            max_g = float(quiz.get("grade", 10) or 10)
            if grade is None or max_g <= 0:
                continue
            pct = float(grade) / max_g * 100
            if qid not in stats:
                stats[qid] = {"name": quiz.get("name", f"Q{qid}")[:20],
                               "scores": [], "pass": 0, "total": 0}
            stats[qid]["scores"].append(pct)
            stats[qid]["total"] += 1
            if pct >= 50:
                stats[qid]["pass"] += 1

    if not stats:
        ax.text(0.5, 0.5, "Sin intentos completados",
                transform=ax.transAxes, ha="center", va="center",
                color=COLORS["text"], fontsize=10)
        ax.set_title("Dificultad de Cuestionarios", fontsize=11, fontweight="bold",
                     color=COLORS["text"])
        return fig

    sorted_stats = sorted(stats.values(),
                          key=lambda x: float(np.mean(x["scores"])))

    names      = [s["name"] for s in sorted_stats]
    avgs       = [float(np.mean(s["scores"])) for s in sorted_stats]
    pass_rates = [s["pass"] / s["total"] * 100 if s["total"] else 0
                  for s in sorted_stats]
    attempts_n = [s["total"] for s in sorted_stats]

    x = np.arange(len(names))
    w = 0.38

    bar_colors = [COLORS["bajo"] if a >= 50 else COLORS["alto"] for a in avgs]
    bars1 = ax.bar(x - w / 2, avgs,       w, color=bar_colors,
                   edgecolor="none", alpha=0.88, label="Nota media (%)")
    bars2 = ax.bar(x + w / 2, pass_rates, w, color=COLORS["primary"],
                   edgecolor="none", alpha=0.75, label="Tasa de aprobados (%)")

    for xi, att_n in zip(x, attempts_n):
        ax.text(xi, 2, f"n={att_n}", ha="center", va="bottom",
                fontsize=7, color=COLORS["fg_dim"])

    ax.axhline(50, color=COLORS["medio"], linestyle="--",
               linewidth=1.2, alpha=0.7, label="Umbral aprobado")
    ax.set_xticks(x)
    ax.set_xticklabels(names, rotation=25, ha="right",
                       fontsize=8, color=COLORS["text"])
    ax.set_ylim(0, 118)
    ax.set_ylabel("Porcentaje (%)")
    ax.set_title("Dificultad por Cuestionario  (más difícil → más fácil)",
                 fontsize=11, fontweight="bold", color=COLORS["text"])
    ax.legend(facecolor=COLORS["bg_card"], labelcolor=COLORS["text"],
              fontsize=8, framealpha=0.9)
    fig.tight_layout()
    return fig


def chart_forum_activity(all_students: List[Dict], forums: List[Dict],
                          figsize=(7, 4)) -> Figure:
    """
    Participación en foros: stacked bar (sin participar / baja / activa)
    por foro, con total de posts anotado arriba.
    """
    fig, ax = plt.subplots(figsize=figsize)
    _apply_dark_style(fig, ax)

    if not forums:
        ax.text(0.5, 0.5, "Sin foros en el curso",
                transform=ax.transAxes, ha="center", va="center",
                color=COLORS["text"], fontsize=10)
        ax.set_title("Participación en Foros", fontsize=11, fontweight="bold",
                     color=COLORS["text"])
        return fig

    forum_stats: Dict[int, Dict] = {}
    for forum in forums:
        fid = forum.get("id")
        if fid is None:
            continue
        forum_stats[fid] = {
            "name":        forum.get("name", f"Foro {fid}")[:28],
            "none":        0,
            "low":         0,
            "active":      0,
            "total_posts": 0,
        }

    total_students = len(all_students)
    for student in all_students:
        pf: Dict[int, int] = {}
        for post in student.get("forum_posts", []):
            fid = post.get("forumid")
            if fid is not None:
                pf[fid] = pf.get(fid, 0) + 1
        for fid in forum_stats:
            cnt = pf.get(fid, 0)
            forum_stats[fid]["total_posts"] += cnt
            if cnt == 0:
                forum_stats[fid]["none"]   += 1
            elif cnt <= 2:
                forum_stats[fid]["low"]    += 1
            else:
                forum_stats[fid]["active"] += 1

    active = sorted(
        [v for v in forum_stats.values() if v["total_posts"] > 0],
        key=lambda x: x["total_posts"], reverse=True,
    )[:10]

    if not active:
        ax.text(0.5, 0.5, "Sin participación en foros registrada",
                transform=ax.transAxes, ha="center", va="center",
                color=COLORS["text"], fontsize=10)
        ax.set_title("Participación en Foros", fontsize=11, fontweight="bold",
                     color=COLORS["text"])
        return fig

    names    = [f["name"]        for f in active]
    none_v   = [f["none"]        for f in active]
    low_v    = [f["low"]         for f in active]
    active_v = [f["active"]      for f in active]
    totals   = [f["total_posts"] for f in active]

    x = np.arange(len(names))
    w = 0.6
    bottom_low    = none_v
    bottom_active = [a + b for a, b in zip(none_v, low_v)]

    ax.bar(x, none_v,   w, color=COLORS["grid"],   edgecolor="none",
           alpha=0.9,  label="Sin participar")
    ax.bar(x, low_v,    w, bottom=bottom_low,
           color=COLORS["medio"],  edgecolor="none", alpha=0.88,
           label="1-2 posts")
    ax.bar(x, active_v, w, bottom=bottom_active,
           color=COLORS["bajo"],   edgecolor="none", alpha=0.88,
           label="3+ posts (activo)")

    for xi, tot in zip(x, totals):
        ax.text(xi, total_students + 0.4,
                f"{tot} posts",
                ha="center", va="bottom",
                color=COLORS["accent"], fontsize=7.5, fontweight="bold")

    ax.set_xticks(x)
    ax.set_xticklabels(names, rotation=25, ha="right",
                       fontsize=8, color=COLORS["text"])
    ax.set_ylabel("N.º Alumnos")
    ax.set_ylim(0, total_students * 1.22 + 1)
    ax.set_title("Participación en Foros",
                 fontsize=11, fontweight="bold", color=COLORS["text"])
    ax.legend(facecolor=COLORS["bg_card"], labelcolor=COLORS["text"],
              fontsize=8, framealpha=0.9)
    fig.tight_layout()
    return fig


# ============================================================
# Gráficas comparativas de todos los cursos
# ============================================================

def chart_all_courses_enrollment(courses: List[Dict], figsize=(9, 5)) -> Figure:
    """
    Barras horizontales con el nº de alumnos matriculados por curso.
    Ordenado de mayor a menor. Muestra hasta 25 cursos.
    """
    fig, ax = plt.subplots(figsize=figsize)
    _apply_dark_style(fig, ax)

    # Filtrar cursos con dato de matriculación y ordenar
    valid = [c for c in courses if c.get("enrolledusercount") not in (None, "?", "")]
    if not valid:
        ax.text(0.5, 0.5, "Sin datos de matriculación disponibles",
                transform=ax.transAxes, ha="center", va="center",
                color=COLORS["text"], fontsize=10)
        ax.set_title("Alumnos Matriculados por Curso",
                     fontsize=11, fontweight="bold", color=COLORS["text"])
        return fig

    valid.sort(key=lambda c: int(c.get("enrolledusercount", 0)), reverse=True)
    valid = valid[:25]  # Máx 25 cursos

    names  = [c.get("shortname") or c.get("fullname", "?")[:22] for c in valid]
    counts = [int(c.get("enrolledusercount", 0)) for c in valid]
    max_c  = max(counts) if counts else 1

    # Colorear por tamaño del curso
    bar_colors = [
        COLORS["bajo"]    if n >= max_c * 0.6 else
        COLORS["primary"] if n >= max_c * 0.25 else
        COLORS["neutral"]
        for n in counts
    ]

    y = np.arange(len(names))
    bars = ax.barh(y, counts, color=bar_colors, edgecolor="none",
                   alpha=0.88, height=0.65, zorder=2)

    for bar, val in zip(bars, counts):
        ax.text(val + max_c * 0.008,
                bar.get_y() + bar.get_height() / 2,
                str(val),
                va="center", color=COLORS["text"], fontsize=8.5, fontweight="bold")

    # Media vertical
    mean_c = float(np.mean(counts))
    ax.axvline(mean_c, color=COLORS["accent"], linestyle="--",
               linewidth=1.5, alpha=0.7, label=f"Media: {mean_c:.0f}")

    ax.set_yticks(y)
    ax.set_yticklabels(names, fontsize=8, color=COLORS["text"])
    ax.set_xlabel("N.º de alumnos matriculados")
    ax.set_xlim(0, max_c * 1.20)
    ax.set_title("Alumnos Matriculados por Curso",
                 fontsize=11, fontweight="bold", color=COLORS["text"])
    ax.legend(facecolor=COLORS["bg_card"], labelcolor=COLORS["text"],
              fontsize=8, framealpha=0.9)
    ax.invert_yaxis()
    fig.tight_layout()
    return fig


# ============================================================
# Nuevas gráficas: Box Plot, Real vs Predicha, Burbujas, Percentil
# ============================================================

def chart_grade_boxplot(all_students: List[Dict], figsize=(10, 5)) -> Figure:
    """
    Box plot de calificaciones por actividad (tomado de grade_items de cada alumno).
    Muestra mediana, cuartiles y outliers para detectar tareas fáciles/difíciles.
    Color del box según mediana: verde ≥70%, naranja ≥50%, rojo <50%.
    """
    fig, ax = plt.subplots(figsize=figsize)
    _apply_dark_style(fig, ax)

    # Agregar grade_items de todos los alumnos por nombre de actividad
    grade_by_act: Dict[str, List[float]] = {}
    for s in all_students:
        for item in s.get("metrics", {}).get("grade_items", []):
            name = (item.get("name") or "?")[:24]
            pct  = item.get("grade_pct")
            if pct is not None:
                grade_by_act.setdefault(name, []).append(float(pct))

    # Filtrar ≥3 datos, ordenar por mediana, top 14
    valid = {k: v for k, v in grade_by_act.items() if len(v) >= 3}
    if not valid:
        ax.text(0.5, 0.5, "Sin calificaciones registradas en el libro de notas",
                transform=ax.transAxes, ha="center", va="center",
                color=COLORS["text"], fontsize=11)
        ax.set_title("Box Plot de Calificaciones por Actividad",
                     fontsize=11, fontweight="bold", color=COLORS["text"])
        fig.tight_layout()
        return fig

    sorted_acts = sorted(valid.items(), key=lambda x: np.median(x[1]))[-14:]
    names = [a[0] for a in sorted_acts]
    data  = [a[1] for a in sorted_acts]

    bp = ax.boxplot(
        data, patch_artist=True, vert=True,
        medianprops=dict(color=COLORS["accent2"], linewidth=2.5),
        whiskerprops=dict(color=COLORS["fg_dim"], linewidth=1.2),
        capprops=dict(color=COLORS["fg_dim"], linewidth=1.2),
        flierprops=dict(marker="o", color=COLORS["alto"],
                        alpha=0.7, markersize=4, linestyle="none"),
    )

    for i, patch in enumerate(bp["boxes"]):
        med = np.median(data[i])
        if med >= 70:
            face = COLORS["bajo"] + "44"
            edge = COLORS["bajo"]
        elif med >= 50:
            face = COLORS["medio"] + "44"
            edge = COLORS["medio"]
        else:
            face = COLORS["alto"] + "44"
            edge = COLORS["alto"]
        patch.set_facecolor(face)
        patch.set_edgecolor(edge)

    ax.set_xticks(range(1, len(names) + 1))
    ax.set_xticklabels(names, rotation=32, ha="right",
                       color=COLORS["text"], fontsize=8)
    ax.axhline(50, color=COLORS["alto"],   linewidth=1.2, linestyle="--",
               alpha=0.6, label="Aprobado (50%)")
    ax.axhline(70, color=COLORS["neutral"], linewidth=0.8, linestyle=":",
               alpha=0.5, label="Notable (70%)")
    ax.set_ylabel("Calificación (%)", color=COLORS["text"])
    ax.set_title("Box Plot de Calificaciones por Actividad",
                 fontsize=11, fontweight="bold", color=COLORS["text"])
    ax.set_ylim(-5, 112)
    ax.legend(facecolor=COLORS["bg_card"], edgecolor=COLORS["border"],
              labelcolor=COLORS["text"], fontsize=8)
    fig.tight_layout()
    return fig


def chart_predicted_vs_actual(all_students: List[Dict], figsize=(8, 4.5)) -> Figure:
    """
    Histogramas solapados: nota real actual vs nota predicha por el modelo.
    Permite comparar la distribución real con lo que predice el modelo.
    """
    fig, ax = plt.subplots(figsize=figsize)
    _apply_dark_style(fig, ax)

    actual    = [s.get("metrics", {}).get("final_grade_pct")
                 for s in all_students
                 if s.get("metrics", {}).get("final_grade_pct") is not None]
    predicted = [s.get("prediction", {}).get("predicted_grade_pct")
                 for s in all_students
                 if s.get("prediction", {}).get("predicted_grade_pct") is not None]

    if not actual and not predicted:
        ax.text(0.5, 0.5, "Sin datos de calificaciones o predicciones",
                transform=ax.transAxes, ha="center", va="center",
                color=COLORS["text"], fontsize=11)
        ax.set_title("Notas Reales vs Predichas", fontsize=11,
                     fontweight="bold", color=COLORS["text"])
        fig.tight_layout()
        return fig

    bins = np.linspace(0, 100, 12)

    if actual:
        ax.hist(actual, bins=bins, color=COLORS["primary"], alpha=0.55,
                label=f"Nota real  (n={len(actual)}, media={np.mean(actual):.1f}%)",
                edgecolor=COLORS["bg"], linewidth=0.5, zorder=2)
        ax.axvline(np.mean(actual), color=COLORS["primary"],
                   linewidth=1.5, linestyle="--", alpha=0.8)

    if predicted:
        ax.hist(predicted, bins=bins, color=COLORS["accent2"], alpha=0.55,
                label=f"Nota predicha (n={len(predicted)}, media={np.mean(predicted):.1f}%)",
                edgecolor=COLORS["bg"], linewidth=0.5, zorder=3)
        ax.axvline(np.mean(predicted), color=COLORS["accent2"],
                   linewidth=1.5, linestyle="--", alpha=0.8)

    # KDE suavizado encima de cada histograma
    if actual and len(actual) > 3:
        xk, yk = _kde_line(actual, 0, 100, bandwidth=10)
        scale = len(actual) * (100 / 11)
        ax.plot(xk, yk * scale, color=COLORS["primary"], linewidth=1.8, alpha=0.9)

    if predicted and len(predicted) > 3:
        xk, yk = _kde_line(predicted, 0, 100, bandwidth=10)
        scale = len(predicted) * (100 / 11)
        ax.plot(xk, yk * scale, color=COLORS["accent2"], linewidth=1.8, alpha=0.9)

    ax.axvline(50, color=COLORS["alto"], linewidth=1.5, linestyle=":",
               alpha=0.7, label="Mínimo aprobado (50%)")

    ax.set_xlabel("Nota (%)", color=COLORS["text"])
    ax.set_ylabel("Número de alumnos", color=COLORS["text"])
    ax.set_title("Distribución: Notas Reales vs Predichas",
                 fontsize=11, fontweight="bold", color=COLORS["text"])
    ax.legend(facecolor=COLORS["bg_card"], edgecolor=COLORS["border"],
              labelcolor=COLORS["text"], fontsize=8)
    fig.tight_layout()
    return fig


def chart_risk_bubble(all_students: List[Dict], figsize=(8, 5)) -> Figure:
    """
    Scatter avanzado — Engagement × Nota actual.
    Tamaño de la burbuja ∝ probabilidad de suspenso.
    Color según nivel de riesgo. Cuadrantes con zona de actuación.
    """
    from matplotlib.lines import Line2D

    fig, ax = plt.subplots(figsize=figsize)
    _apply_dark_style(fig, ax)

    risk_color_map = {
        "alto":  COLORS["alto"],
        "medio": COLORS["medio"],
        "bajo":  COLORS["bajo"],
    }

    has_data = False
    for s in all_students:
        m    = s.get("metrics", {})
        p    = s.get("prediction", {})
        eng  = m.get("engagement_score", 0)
        grade = m.get("final_grade_pct")
        if grade is None:
            continue
        has_data = True
        risk_prob = float(p.get("risk_probability", 0.1))
        risk      = s.get("risk_level", "bajo")
        color     = risk_color_map.get(risk, COLORS["neutral"])
        size      = max(30, risk_prob * 900)
        ax.scatter(eng, grade, s=size, c=color, alpha=0.72,
                   edgecolors=COLORS["bg"], linewidths=0.6, zorder=3)

    if not has_data:
        ax.text(0.5, 0.5, "Sin datos suficientes (se necesitan notas activas)",
                transform=ax.transAxes, ha="center", va="center",
                color=COLORS["text"], fontsize=11)
        ax.set_title("Mapa de Riesgo: Engagement × Nota",
                     fontsize=11, fontweight="bold", color=COLORS["text"])
        fig.tight_layout()
        return fig

    # Líneas de referencia
    ax.axhline(50, color=COLORS["alto"],    linewidth=1.2, linestyle="--", alpha=0.5)
    ax.axvline(40, color=COLORS["neutral"], linewidth=1.0, linestyle="--", alpha=0.4)

    # Sombreado de la zona crítica
    ax.fill_between([0, 40], 0, 50, color=COLORS["alto"], alpha=0.06)

    # Etiquetas de cuadrante
    fs = 7.5
    ax.text(2,  97, "Bajo eng. / Alta nota",     color=COLORS["fg_dim"], fontsize=fs)
    ax.text(42, 97, "✓ Engagement + nota alta",  color=COLORS["bajo"],   fontsize=fs)
    ax.text(2,   3, "⚠ ZONA CRÍTICA",            color=COLORS["alto"],   fontsize=fs, fontweight="bold")
    ax.text(42,  3, "Eng. ok · nota baja",        color=COLORS["medio"],  fontsize=fs)

    # Leyenda de riesgo + nota sobre el tamaño
    legend_elements = [
        Line2D([0], [0], marker="o", color="w", label="Riesgo alto",
               markerfacecolor=COLORS["alto"],  markersize=10),
        Line2D([0], [0], marker="o", color="w", label="Riesgo medio",
               markerfacecolor=COLORS["medio"], markersize=7),
        Line2D([0], [0], marker="o", color="w", label="Riesgo bajo",
               markerfacecolor=COLORS["bajo"],  markersize=5),
        Line2D([0], [0], linestyle="none", label="Tamaño ∝ prob. suspenso"),
    ]
    ax.legend(handles=legend_elements, facecolor=COLORS["bg_card"],
              edgecolor=COLORS["border"], labelcolor=COLORS["text"], fontsize=8)

    ax.set_xlabel("Engagement (0–100)", color=COLORS["text"])
    ax.set_ylabel("Nota actual (%)", color=COLORS["text"])
    ax.set_title("Mapa de Riesgo: Engagement × Nota × Prob. Suspenso",
                 fontsize=11, fontweight="bold", color=COLORS["text"])
    ax.set_xlim(-2, 102)
    ax.set_ylim(-2, 106)
    fig.tight_layout()
    return fig


def chart_student_percentile(student: Dict, all_students: List[Dict],
                              figsize=(7, 4.5)) -> Figure:
    """
    Barras horizontales que muestran en qué percentil se encuentra el alumno
    para cada métrica clave en comparación con el resto de la clase.
    Verde = top, naranja = medio, rojo = bajo.
    """
    fig, ax = plt.subplots(figsize=figsize)
    _apply_dark_style(fig, ax)

    m = student.get("metrics", {})

    # (etiqueta, clave_métrica, mayor=mejor)
    metrics_def = [
        ("Nota final",        "final_grade_pct",     True),
        ("Engagement",        "engagement_score",    True),
        ("Tasa de entregas",  "submission_rate",     True),
        ("Completitud",       "completion_rate",     True),
        ("Quiz avg",          "quiz_avg_pct",        True),
        ("Posts en foros",    "forum_posts_count",   True),
        ("Días sin acceso",   "days_since_access",   False),  # menor = mejor
    ]

    labels, percentiles, colors_list = [], [], []

    for label, key, higher_better in metrics_def:
        val = m.get(key)
        if val is None:
            continue
        all_vals = [s.get("metrics", {}).get(key)
                    for s in all_students
                    if s.get("metrics", {}).get(key) is not None]
        if len(all_vals) < 2:
            continue
        below = sum(1 for v in all_vals if v < val)
        pct   = below / len(all_vals) * 100
        if not higher_better:
            pct = 100 - pct
        labels.append(label)
        percentiles.append(pct)
        colors_list.append(
            COLORS["bajo"]   if pct >= 65 else
            COLORS["medio"]  if pct >= 35 else
            COLORS["alto"]
        )

    if not labels:
        ax.text(0.5, 0.5, "Sin datos suficientes para calcular percentiles",
                transform=ax.transAxes, ha="center", va="center",
                color=COLORS["text"], fontsize=11)
        ax.set_title("Posición del Alumno en el Grupo",
                     fontsize=11, fontweight="bold", color=COLORS["text"])
        fig.tight_layout()
        return fig

    y    = np.arange(len(labels))
    bars = ax.barh(y, percentiles, color=colors_list, height=0.55,
                   alpha=0.85, edgecolor="none", zorder=2)

    # Etiqueta numérica en cada barra
    for bar, pct in zip(bars, percentiles):
        x_lbl = min(pct + 2, 92)
        ax.text(x_lbl, bar.get_y() + bar.get_height() / 2,
                f"{pct:.0f}° pct.", va="center",
                color=COLORS["text"], fontsize=8.5)

    # Línea mediana + zona neutra
    ax.axvline(50, color=COLORS["fg_dim"], linewidth=1.2,
               linestyle="--", alpha=0.6, label="Mediana (50°)")
    ax.fill_betweenx([-0.5, len(labels) - 0.5], 35, 65,
                     color=COLORS["neutral"], alpha=0.06)

    ax.set_yticks(y)
    ax.set_yticklabels(labels, color=COLORS["text"], fontsize=9)
    ax.set_xlim(0, 104)
    ax.set_xlabel("Percentil en el grupo (100 = mejor de la clase)",
                  color=COLORS["text"])
    ax.set_title(
        f"Posición de {student.get('fullname', 'Alumno')[:30]} en el Grupo",
        fontsize=11, fontweight="bold", color=COLORS["text"])
    ax.legend(facecolor=COLORS["bg_card"], edgecolor=COLORS["border"],
              labelcolor=COLORS["text"], fontsize=8)
    fig.tight_layout()
    return fig


def chart_all_courses_categories(courses: List[Dict], figsize=(6, 5)) -> Figure:
    """
    Donut de distribución de cursos por categoría.
    Muestra nº de cursos y total de alumnos por categoría.
    """
    fig, ax = plt.subplots(figsize=figsize)
    _apply_dark_style(fig, ax)
    ax.spines["bottom"].set_visible(False)
    ax.spines["left"].set_visible(False)
    ax.set_xticks([])
    ax.set_yticks([])

    if not courses:
        ax.text(0.5, 0.5, "Sin cursos disponibles",
                transform=ax.transAxes, ha="center", va="center",
                color=COLORS["text"], fontsize=10)
        ax.set_title("Cursos por Categoría", fontsize=11, fontweight="bold",
                     color=COLORS["text"])
        return fig

    # Agrupar por categoría
    cat_counts: Dict[str, int] = {}
    cat_students: Dict[str, int] = {}
    for c in courses:
        cat = str(c.get("categoryname") or c.get("category") or "Sin categoría")
        cat_counts[cat]   = cat_counts.get(cat, 0) + 1
        enroll = c.get("enrolledusercount")
        if enroll not in (None, "?", ""):
            cat_students[cat] = cat_students.get(cat, 0) + int(enroll)

    # Ordenar por nº de cursos, agrupar categorías pequeñas en "Otras"
    sorted_cats = sorted(cat_counts.items(), key=lambda x: x[1], reverse=True)
    if len(sorted_cats) > 8:
        top = sorted_cats[:7]
        other_count = sum(v for _, v in sorted_cats[7:])
        other_students = sum(cat_students.get(k, 0) for k, _ in sorted_cats[7:])
        top.append(("Otras", other_count))
        cat_students["Otras"] = other_students
        sorted_cats = top

    labels = [k for k, _ in sorted_cats]
    values = [v for _, v in sorted_cats]
    total  = sum(values)

    # Paleta de colores variada
    palette = [
        COLORS["primary"], COLORS["accent"], COLORS["bajo"], COLORS["secondary"],
        COLORS["accent2"], COLORS["medio"], COLORS["alto"], COLORS["neutral"],
    ]
    colors = [palette[i % len(palette)] for i in range(len(labels))]

    wedges, texts, autotexts = ax.pie(
        values,
        labels=None,
        autopct="%1.0f%%",
        colors=colors,
        startangle=90,
        pctdistance=0.80,
        wedgeprops={"linewidth": 2, "edgecolor": COLORS["bg"]},
    )
    for at in autotexts:
        at.set_color("white")
        at.set_fontsize(7.5)
        at.set_fontweight("bold")

    # Agujero central
    circle = plt.Circle((0, 0), 0.54, color=COLORS["bg_card"])
    ax.add_patch(circle)
    ax.text(0,  0.10, str(total), ha="center", va="center",
            fontsize=24, fontweight="bold", color=COLORS["text"])
    ax.text(0, -0.12, "cursos", ha="center", va="center",
            fontsize=9, color=COLORS["fg_dim"])

    # Leyenda con nº de cursos y alumnos
    legend_labels = [
        f"{lbl}  ({cnt} cursos" +
        (f" · {cat_students[lbl]} al." if cat_students.get(lbl) else "") + ")"
        for lbl, cnt in zip(labels, values)
    ]
    ax.legend(
        wedges, legend_labels,
        loc="lower center", bbox_to_anchor=(0.5, -0.22),
        ncol=2, fontsize=7.5,
        facecolor=COLORS["bg_card"], labelcolor=COLORS["text"],
        framealpha=0.9,
    )
    ax.set_title("Distribución por Categoría",
                 fontsize=11, fontweight="bold", color=COLORS["text"])
    fig.tight_layout()
    return fig
