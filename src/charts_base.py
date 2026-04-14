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
