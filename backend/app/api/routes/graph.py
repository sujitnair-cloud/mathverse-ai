from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from app.services.graph_service import (
    build_function_graph, build_bar_chart, build_histogram,
    build_scatter_plot, build_3d_surface
)

router = APIRouter()


class GraphRequest(BaseModel):
    expressions: List[str]
    x_min: Optional[float] = -10
    x_max: Optional[float] = 10
    title: Optional[str] = ""
    graph_type: Optional[str] = "function"


class BarChartRequest(BaseModel):
    labels: List[str]
    values: List[float]
    title: Optional[str] = "Bar Chart"


class ScatterRequest(BaseModel):
    x: List[float]
    y: List[float]
    title: Optional[str] = "Scatter Plot"


class Surface3DRequest(BaseModel):
    expression: str
    x_min: Optional[float] = -5
    x_max: Optional[float] = 5
    y_min: Optional[float] = -5
    y_max: Optional[float] = 5


@router.post("/graph")
async def plot_functions(req: GraphRequest):
    if not req.expressions:
        raise HTTPException(status_code=400, detail="At least one expression required.")
    if req.x_min >= req.x_max:
        raise HTTPException(status_code=400, detail="x_min must be less than x_max.")

    data = build_function_graph(req.expressions, req.x_min, req.x_max, req.title)
    return data


@router.post("/graph/bar")
async def bar_chart(req: BarChartRequest):
    return build_bar_chart(req.labels, req.values, req.title)


@router.post("/graph/scatter")
async def scatter_plot(req: ScatterRequest):
    return build_scatter_plot(req.x, req.y, req.title)


@router.post("/graph/3d")
async def surface_3d(req: Surface3DRequest):
    data = build_3d_surface(
        req.expression,
        (req.x_min, req.x_max),
        (req.y_min, req.y_max),
    )
    if "error" in data:
        raise HTTPException(status_code=422, detail=data["error"])
    return data
