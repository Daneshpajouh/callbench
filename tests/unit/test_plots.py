from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace

import matplotlib.pyplot as plt
import pandas as pd
import pytest
from matplotlib.patches import Rectangle
from plots import f1_figure, runtime_figure
from smk_stub import DATA, make_smk, run_as_rule_script

COLUMNS = ["sample", "caller", "stratum", "type", "f1"]


@pytest.fixture(autouse=True)
def _close_figures() -> Iterator[None]:
    yield
    plt.close("all")


def _acc(rows: list[tuple[str, str, str, str, object]]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=COLUMNS)


def _is_svg(path: Path) -> bool:
    head = path.read_text()[:400]
    return path.stat().st_size > 0 and "<svg" in path.read_text() and head.startswith("<?xml")


def test_f1_figure_writes_an_svg(tmp_path: Path) -> None:
    out = tmp_path / "f1.svg"
    f1_figure(
        _acc(
            [
                ("HG002", "bcftools", "all", "SNV", 0.99),
                ("HG002", "freebayes", "all", "SNV", 0.98),
                ("HG002", "bcftools", "all", "INDEL", 0.9),
                ("HG002", "freebayes", "low_complexity", "INDEL", 0.7),
            ]
        ),
        str(out),
    )
    assert _is_svg(out)


@pytest.mark.parametrize(
    "rows",
    [
        pytest.param([], id="empty-table"),
        pytest.param(
            [("s", "bcftools", "all", "SNV", 0.9), ("s", "bcftools", "all", "INDEL", None)],
            id="no-indel-values",
        ),
        pytest.param(
            [("s", "bcftools", "all", "SNV", "NA"), ("s", "bcftools", "all", "INDEL", "NA")],
            id="every-value-is-the-string-NA",
        ),
        pytest.param(
            [("s", "bcftools", "all", "SNV", 0.9), ("s", "freebayes", "all", "SNV", None)],
            id="one-caller-missing-in-a-panel",
        ),
        pytest.param([("s", "bcftools", "all", "OTHER", 0.5)], id="unknown-variant-type-only"),
        pytest.param([("s", "bcftools", "all", "SNV", "0.9500")], id="values-as-text"),
        pytest.param([("s", "bcftools", "all", "SNV", 0.9)] * 3, id="duplicate-rows-are-averaged"),
    ],
)
def test_f1_figure_edge_cases(
    tmp_path: Path, rows: list[tuple[str, str, str, str, object]]
) -> None:
    out = tmp_path / "f1.svg"
    f1_figure(_acc(rows), str(out))
    assert _is_svg(out)


def test_f1_figure_does_not_change_its_input(tmp_path: Path) -> None:
    acc = _acc([("s", "bcftools", "all", "SNV", "0.9")])
    f1_figure(acc, str(tmp_path / "f1.svg"))
    assert acc["f1"].tolist() == ["0.9"]


def test_runtime_figure_writes_an_svg(tmp_path: Path) -> None:
    out = tmp_path / "runtime.svg"
    runtime_figure(
        pd.DataFrame({"rule": ["bwa_mem", "vcfeval"], "wall_s_total": [120.0, 30.5]}), str(out)
    )
    assert _is_svg(out)


@pytest.mark.parametrize(
    "frame",
    [
        pytest.param(pd.DataFrame({"rule": [], "wall_s_total": []}), id="no-rules"),
        pytest.param(pd.DataFrame({"rule": ["a"], "wall_s_total": [0.0]}), id="zero-time"),
        pytest.param(
            pd.DataFrame({"rule": ["a", "b"], "wall_s_total": [1.0, float("nan")]}), id="na-time"
        ),
        pytest.param(
            pd.DataFrame({"rule": [f"r{i}" for i in range(40)], "wall_s_total": range(40)}),
            id="many-rules",
        ),
    ],
)
def test_runtime_figure_edge_cases(tmp_path: Path, frame: pd.DataFrame) -> None:
    out = tmp_path / "runtime.svg"
    runtime_figure(frame, str(out))
    assert _is_svg(out)


def test_rule_script_writes_both_figures(tmp_path: Path) -> None:
    profiling = tmp_path / "profiling.tsv"
    profiling.write_text("rule\twall_s_total\nbwa_mem\t12.5\nvcfeval\t3.0\n")
    smk = make_smk(
        tmp_path,
        "plots",
        input=SimpleNamespace(
            accuracy=str(DATA / "accuracy_observed_with_na.tsv"), profiling=str(profiling)
        ),
        output=SimpleNamespace(f1=str(tmp_path / "f1.svg"), runtime=str(tmp_path / "rt.svg")),
    )
    run_as_rule_script("plots", smk)
    assert _is_svg(tmp_path / "f1.svg") and _is_svg(tmp_path / "rt.svg")
    assert "read 3 accuracy rows and 2 profiling rows" in (tmp_path / "plots.log").read_text()


def test_rule_script_names_an_empty_input_table(tmp_path: Path) -> None:
    empty = tmp_path / "empty.tsv"
    empty.write_text("")
    smk = make_smk(
        tmp_path,
        "plots",
        input=SimpleNamespace(accuracy=str(empty), profiling=str(empty)),
        output=SimpleNamespace(f1=str(tmp_path / "f1.svg"), runtime=str(tmp_path / "rt.svg")),
    )
    with pytest.raises(ValueError, match=r"empty\.tsv: empty file"):
        run_as_rule_script("plots", smk)
    assert "ERROR rule=plots sample=- ValueError: " in (tmp_path / "plots.log").read_text()


def test_f1_figure_draws_the_given_values(tmp_path: Path) -> None:
    acc = _acc(
        [
            ("HG002", "bcftools", "all", "SNV", 0.99),
            ("HG002", "freebayes", "all", "SNV", 0.95),
            ("HG002", "bcftools", "all", "INDEL", 0.90),
            ("HG002", "freebayes", "all", "INDEL", "NA"),
        ]
    )
    f1_figure(acc, str(tmp_path / "f1.svg"))
    snv, indel = plt.gcf().axes
    assert sorted(round(p.get_height(), 4) for p in snv.patches if isinstance(p, Rectangle)) == [
        0.95,
        0.99,
    ]
    # The NA freebayes indel value is not drawn as a bar of height 0.
    heights = [round(p.get_height(), 4) for p in indel.patches if isinstance(p, Rectangle)]
    assert 0.9 in heights and 0.0 not in heights


def test_runtime_figure_draws_one_bar_per_rule_in_sorted_order(tmp_path: Path) -> None:
    by_rule = pd.DataFrame({"rule": ["call", "align", "qc"], "wall_s_total": [27.3, 120.5, 3.0]})
    runtime_figure(by_rule, str(tmp_path / "runtime.svg"))
    (ax,) = plt.gcf().axes
    assert [p.get_width() for p in ax.patches if isinstance(p, Rectangle)] == [3.0, 27.3, 120.5]
    assert [t.get_text() for t in ax.get_yticklabels()] == ["qc", "call", "align"]


def test_f1_figure_legend_covers_no_bars(tmp_path: Path) -> None:
    f1_figure(
        _acc(
            [
                ("HG002", "bcftools", "all", "SNV", 0.99),
                ("HG002", "freebayes", "all", "SNV", 0.98),
                ("HG002", "bcftools", "all", "INDEL", 0.9),
                ("HG002", "freebayes", "all", "INDEL", 0.93),
            ]
        ),
        str(tmp_path / "f1.svg"),
    )
    fig = plt.gcf()
    renderer = fig.canvas.get_renderer()  # type: ignore[attr-defined]
    assert all(ax.get_legend() is None for ax in fig.axes)
    (legend,) = fig.legends
    box = legend.get_window_extent(renderer)
    assert not any(box.overlaps(ax.get_window_extent(renderer)) for ax in fig.axes)
    assert [t.get_text() for t in legend.get_texts()] == ["bcftools", "freebayes"]


def test_f1_figure_keeps_each_callers_colour_when_one_is_missing(tmp_path: Path) -> None:
    acc = _acc(
        [
            ("HG002", "bcftools", "all", "SNV", 0.99),
            ("HG002", "freebayes", "all", "SNV", 0.98),
            ("HG002", "freebayes", "all", "INDEL", 0.93),
        ]
    )
    f1_figure(acc, str(tmp_path / "f1.svg"))
    snv, indel = plt.gcf().axes
    snv_colours = [p.get_facecolor() for p in snv.patches if isinstance(p, Rectangle)]
    indel_colours = [p.get_facecolor() for p in indel.patches if isinstance(p, Rectangle)]
    # SNV bars are bcftools then freebayes; the only INDEL bar is freebayes.
    assert indel_colours == [snv_colours[1]]
    assert snv_colours[0] != snv_colours[1]
