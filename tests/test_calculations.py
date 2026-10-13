import time

from radixscope.calculations import CalculationJob, CalculationResult


def completed(job: CalculationJob) -> CalculationResult:
    deadline = time.monotonic() + 20
    try:
        while time.monotonic() < deadline:
            result = job.poll()
            if result is not None:
                return result
            time.sleep(0.01)
        raise AssertionError("worker did not finish")
    finally:
        job.cancel()


def test_isolated_worker_returns_exact_report_and_domain_error() -> None:
    state: dict[str, object] = {
        "input": "1/3", "source_base": 10, "target_base": 2, "limit": 4,
    }
    job = CalculationJob("Trace", state)
    result = completed(job)
    assert result.report is not None and result.report["result"] == "0.(01)"
    assert "exact: 1/3" in result.text and not result.error
    assert not job.directory.exists()
    state["input"] = "1/0"
    result = completed(CalculationJob("Trace", state))
    assert result.error and result.report is None


def test_cancel_reaps_worker_and_removes_temporary_files() -> None:
    job = CalculationJob("Conversion", {
        "input": "2 ** 1000000000", "mode": "Expression", "source_base": 10,
        "targets": "2", "exact_output": True, "precision": 16, "rounding": "half-even",
    })
    process = job.process
    assert process is not None
    job.cancel()
    assert process.poll() is not None
    assert not job.directory.exists()
    job.cancel()
