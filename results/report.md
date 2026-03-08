# Experiment Report

## Summary Table
| Run | Count | Avg Score | Std | Avg Len | Avg Citations | Avg Sources |
|---|---|---|---|---|---|---|
| baseline_auto | 2 | 0.815 | 0.029 | 810.0 | 9.0 | 5.0 |
| more_sources | 2 | 0.828 | 0.016 | 839.5 | 11.5 | 8.0 |
| qwen_7b | 2 | 0.828 | 0.016 | 853.5 | 13.0 | 5.0 |
| llama3_8b | 2 | 0.685 | 0.015 | 678.5 | 5.0 | 5.0 |

## LaTeX Table
```latex
\begin{tabular}{lrrrrrr}
\toprule
Run & Count & AvgScore & Std & AvgLen & AvgCite & AvgSrc \\
\midrule
baseline_auto & 2 & 0.815 & 0.029 & 810.0 & 9.0 & 5.0 \\
more_sources & 2 & 0.828 & 0.016 & 839.5 & 11.5 & 8.0 \\
qwen_7b & 2 & 0.828 & 0.016 & 853.5 & 13.0 & 5.0 \\
llama3_8b & 2 & 0.685 & 0.015 & 678.5 & 5.0 & 5.0 \\
\bottomrule
\end{tabular}
```

## Plots
![Average Scores](avg_scores.png)

![Average Sources](avg_sources.png)

![Radar Metrics](radar_metrics.png)

![Score Error Bars](score_errorbars.png)
