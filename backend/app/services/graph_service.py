"""
Graph generation service using Plotly for interactive charts.
Returns JSON data for frontend Plotly rendering.
"""
import numpy as np
import json
from typing import List, Optional, Dict, Any
from app.services.math_engine import generate_function_points


def build_function_graph(
    expressions: List[str],
    x_min: float = -10,
    x_max: float = 10,
    title: str = "",
) -> Dict[str, Any]:
    """Build Plotly-compatible JSON for one or more mathematical functions."""
    traces = []
    colors = ["#6366f1", "#ec4899", "#10b981", "#f59e0b", "#3b82f6"]

    for i, expr in enumerate(expressions):
        data = generate_function_points(expr, x_min, x_max)
        if "error" in data:
            continue
        traces.append({
            "type": "scatter",
            "mode": "lines",
            "name": f"f(x) = {data['expr']}",
            "x": data["x"],
            "y": data["y"],
            "line": {"color": colors[i % len(colors)], "width": 2.5},
        })

    layout = {
        "title": title or "Function Graph",
        "xaxis": {
            "title": "x",
            "zeroline": True,
            "zerolinewidth": 1,
            "zerolinecolor": "#6b7280",
            "gridcolor": "#374151",
        },
        "yaxis": {
            "title": "f(x)",
            "zeroline": True,
            "zerolinewidth": 1,
            "zerolinecolor": "#6b7280",
            "gridcolor": "#374151",
        },
        "paper_bgcolor": "#1f2937",
        "plot_bgcolor": "#111827",
        "font": {"color": "#f9fafb"},
        "legend": {"bgcolor": "#374151"},
        "margin": {"l": 50, "r": 30, "t": 50, "b": 50},
    }

    return {"data": traces, "layout": layout}


def build_bar_chart(labels: List[str], values: List[float], title: str = "Bar Chart") -> Dict:
    return {
        "data": [{
            "type": "bar",
            "x": labels,
            "y": values,
            "marker": {"color": "#6366f1"},
        }],
        "layout": {
            "title": title,
            "paper_bgcolor": "#1f2937",
            "plot_bgcolor": "#111827",
            "font": {"color": "#f9fafb"},
        },
    }


def build_histogram(values: List[float], title: str = "Histogram", bins: int = 20) -> Dict:
    return {
        "data": [{
            "type": "histogram",
            "x": values,
            "nbinsx": bins,
            "marker": {"color": "#6366f1", "opacity": 0.8},
        }],
        "layout": {
            "title": title,
            "xaxis": {"title": "Value"},
            "yaxis": {"title": "Frequency"},
            "paper_bgcolor": "#1f2937",
            "plot_bgcolor": "#111827",
            "font": {"color": "#f9fafb"},
        },
    }


def build_scatter_plot(x: List[float], y: List[float], title: str = "Scatter Plot") -> Dict:
    return {
        "data": [{
            "type": "scatter",
            "mode": "markers",
            "x": x,
            "y": y,
            "marker": {"color": "#ec4899", "size": 8, "opacity": 0.7},
        }],
        "layout": {
            "title": title,
            "paper_bgcolor": "#1f2937",
            "plot_bgcolor": "#111827",
            "font": {"color": "#f9fafb"},
        },
    }


def build_3d_surface(expr_str: str, x_range: tuple = (-5, 5), y_range: tuple = (-5, 5), grid: int = 50) -> Dict:
    """Build a 3D surface plot for f(x, y)."""
    import sympy as sp
    x_sym, y_sym = sp.symbols("x y")
    try:
        expr = sp.sympify(expr_str.replace("^", "**"))
        f = sp.lambdify((x_sym, y_sym), expr, modules=["numpy"])
        x_vals = np.linspace(x_range[0], x_range[1], grid)
        y_vals = np.linspace(y_range[0], y_range[1], grid)
        X, Y = np.meshgrid(x_vals, y_vals)
        Z = f(X, Y)
        Z = np.where(np.isfinite(Z), Z, 0)
        return {
            "data": [{
                "type": "surface",
                "x": x_vals.tolist(),
                "y": y_vals.tolist(),
                "z": Z.tolist(),
                "colorscale": "Viridis",
            }],
            "layout": {
                "title": f"z = {expr_str}",
                "scene": {"xaxis_title": "x", "yaxis_title": "y", "zaxis_title": "z"},
                "paper_bgcolor": "#1f2937",
                "font": {"color": "#f9fafb"},
            },
        }
    except Exception as e:
        return {"error": str(e)}
