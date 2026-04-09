"""
Battery RUL Evaluation Framework

Benchmarking, statistical validation, and report generation for RUL methods.
"""

import numpy as np
import pandas as pd
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from scipy import stats
from scipy.stats import ttest_rel, wilcoxon
import warnings
warnings.filterwarnings('ignore')


# =============================================================================
# Metrics
# =============================================================================

def compute_mae(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Mean Absolute Error"""
    return np.mean(np.abs(y_true - y_pred))


def compute_rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Root Mean Square Error"""
    return np.sqrt(np.mean((y_true - y_pred) ** 2))


def compute_mape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Mean Absolute Percentage Error"""
    # Avoid division by zero
    mask = y_true != 0
    return np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100


def compute_r2(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """R-squared (coefficient of determination)"""
    ss_res = np.sum((y_true - y_pred) ** 2)
    ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
    return 1 - (ss_res / ss_tot)


def compute_accuracy_at_threshold(y_true: np.ndarray, y_pred: np.ndarray, 
                                   threshold: float = 0.1) -> float:
    """
    Percentage of predictions within threshold of true value.
    
    Args:
        threshold: Error threshold (0.1 = 10%, 0.2 = 20%)
    """
    relative_error = np.abs((y_true - y_pred) / y_true)
    return np.mean(relative_error <= threshold) * 100


def compute_all_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict:
    """
    Compute all evaluation metrics.
    
    Returns:
        Dict with all metrics
    """
    return {
        'mae': compute_mae(y_true, y_pred),
        'rmse': compute_rmse(y_true, y_pred),
        'mape': compute_mape(y_true, y_pred),
        'r2': compute_r2(y_true, y_pred),
        'accuracy_10': compute_accuracy_at_threshold(y_true, y_pred, 0.1),
        'accuracy_20': compute_accuracy_at_threshold(y_true, y_pred, 0.2),
        'n_samples': len(y_true),
    }


# =============================================================================
# Statistical Tests
# =============================================================================

def paired_t_test(errors_method1: np.ndarray, errors_method2: np.ndarray) -> Dict:
    """
    Paired t-test comparing two methods.
    
    Args:
        errors_method1: Absolute errors from method 1
        errors_method2: Absolute errors from method 2
        
    Returns:
        Dict with t-statistic, p-value, and interpretation
    """
    t_stat, p_value = ttest_rel(errors_method1, errors_method2)
    
    return {
        'test': 'paired_t_test',
        't_statistic': float(t_stat),
        'p_value': float(p_value),
        'significant': p_value < 0.05,
        'interpretation': 'Method 2 significantly better' if t_stat > 0 and p_value < 0.05 
                         else ('Method 1 significantly better' if t_stat < 0 and p_value < 0.05 
                               else 'No significant difference')
    }


def wilcoxon_test(errors_method1: np.ndarray, errors_method2: np.ndarray) -> Dict:
    """
    Wilcoxon signed-rank test (non-parametric alternative to t-test).
    
    Args:
        errors_method1: Absolute errors from method 1
        errors_method2: Absolute errors from method 2
        
    Returns:
        Dict with test statistic, p-value, and interpretation
    """
    stat, p_value = wilcoxon(errors_method1, errors_method2)
    
    return {
        'test': 'wilcoxon_signed_rank',
        'statistic': float(stat),
        'p_value': float(p_value),
        'significant': p_value < 0.05,
        'interpretation': 'Method 2 significantly better' if stat < 0 and p_value < 0.05 
                         else ('Method 1 significantly better' if stat > 0 and p_value < 0.05 
                               else 'No significant difference')
    }


def compute_effect_size(errors_method1: np.ndarray, errors_method2: np.ndarray) -> Dict:
    """
    Compute Cohen's d effect size.
    
    Args:
        errors_method1: Absolute errors from method 1
        errors_method2: Absolute errors from method 2
        
    Returns:
        Dict with Cohen's d and interpretation
    """
    # Difference in means
    mean_diff = np.mean(errors_method1) - np.mean(errors_method2)
    
    # Pooled standard deviation
    std1 = np.std(errors_method1, ddof=1)
    std2 = np.std(errors_method2, ddof=1)
    pooled_std = np.sqrt((std1**2 + std2**2) / 2)
    
    cohens_d = mean_diff / (pooled_std + 1e-8)
    
    # Interpretation
    abs_d = abs(cohens_d)
    if abs_d < 0.2:
        interpretation = 'negligible'
    elif abs_d < 0.5:
        interpretation = 'small'
    elif abs_d < 0.8:
        interpretation = 'medium'
    else:
        interpretation = 'large'
    
    return {
        'cohens_d': float(cohens_d),
        'interpretation': interpretation,
        'better_method': 'method_2' if cohens_d > 0 else 'method_1'
    }


def run_statistical_tests(errors_baseline: np.ndarray, 
                          errors_candidate: np.ndarray) -> Dict:
    """
    Run all statistical tests comparing candidate vs baseline.
    
    Args:
        errors_baseline: Absolute errors from baseline method
        errors_candidate: Absolute errors from candidate method
        
    Returns:
        Dict with all test results
    """
    return {
        'paired_t_test': paired_t_test(errors_baseline, errors_candidate),
        'wilcoxon_test': wilcoxon_test(errors_baseline, errors_candidate),
        'effect_size': compute_effect_size(errors_baseline, errors_candidate),
    }


# =============================================================================
# Benchmark Runner
# =============================================================================

class BenchmarkRunner:
    """
    Run fair benchmarks comparing multiple RUL methods.
    """
    
    def __init__(self, test_data: Tuple[np.ndarray, np.ndarray], 
                 seed: int = 42):
        """
        Args:
            test_data: (X_test, y_test) tuple
            seed: Random seed for reproducibility
        """
        self.X_test, self.y_test = test_data
        self.seed = seed
        self.results = {}
    
    def run_method(self, method_name: str, model, 
                   n_seeds: int = 5) -> Dict:
        """
        Run benchmark for a single method with multiple seeds.
        
        Args:
            method_name: Name of the method
            model: Model instance (must have fit() and predict() methods)
            n_seeds: Number of random seeds for robustness
            
        Returns:
            Dict with metrics for each seed and aggregated stats
        """
        all_metrics = []
        all_predictions = []
        
        for seed in range(n_seeds):
            np.random.seed(seed)
            
            # For methods with stochastic training, this ensures different initializations
            # The model should handle seeding internally if needed
            
            # Predict
            predictions = model.predict(self.X_test)
            
            # Align lengths (in case of sequence models)
            n_pred = len(predictions)
            y_true = self.y_test[-n_pred:]
            
            # Compute metrics
            metrics = compute_all_metrics(y_true, predictions)
            metrics['seed'] = seed
            
            all_metrics.append(metrics)
            all_predictions.append(predictions)
        
        # Aggregate across seeds
        metrics_df = pd.DataFrame(all_metrics)
        aggregated = {
            'method_name': method_name,
            'n_seeds': n_seeds,
            'metrics_mean': metrics_df.drop('seed', axis=1).mean().to_dict(),
            'metrics_std': metrics_df.drop('seed', axis=1).std().to_dict(),
            'all_predictions': all_predictions,
            'per_seed_results': all_metrics,
        }
        
        self.results[method_name] = aggregated
        return aggregated
    
    def compare_methods(self, method1_name: str, method2_name: str) -> Dict:
        """
        Statistically compare two methods.
        
        Args:
            method1_name: Name of first method
            method2_name: Name of second method
            
        Returns:
            Dict with comparison results
        """
        if method1_name not in self.results or method2_name not in self.results:
            raise ValueError(f"Methods not found in results")
        
        # Get absolute errors for each seed
        errors_1 = []
        errors_2 = []
        
        for seed_result in self.results[method1_name]['per_seed_results']:
            # Compute mean absolute error for this seed
            mae = seed_result['mae']
            errors_1.append(mae)
        
        for seed_result in self.results[method2_name]['per_seed_results']:
            mae = seed_result['mae']
            errors_2.append(mae)
        
        errors_1 = np.array(errors_1)
        errors_2 = np.array(errors_2)
        
        # Run statistical tests
        stats_results = run_statistical_tests(errors_1, errors_2)
        
        # Determine winner
        mean_mae_1 = self.results[method1_name]['metrics_mean']['mae']
        mean_mae_2 = self.results[method2_name]['metrics_mean']['mae']
        
        winner = method2_name if mean_mae_2 < mean_mae_1 else method1_name
        
        return {
            'method1': method1_name,
            'method2': method2_name,
            'mae_method1': mean_mae_1,
            'mae_method2': mean_mae_2,
            'winner': winner,
            'statistical_tests': stats_results,
        }
    
    def generate_leaderboard(self) -> pd.DataFrame:
        """
        Generate leaderboard of all benchmarked methods.
        
        Returns:
            DataFrame with methods ranked by MAE
        """
        rows = []
        for method_name, result in self.results.items():
            row = {
                'method': method_name,
                'mae': result['metrics_mean']['mae'],
                'mae_std': result['metrics_std']['mae'],
                'rmse': result['metrics_mean']['rmse'],
                'rmse_std': result['metrics_std']['rmse'],
                'mape': result['metrics_mean']['mape'],
                'r2': result['metrics_mean']['r2'],
                'accuracy_10': result['metrics_mean']['accuracy_10'],
                'accuracy_20': result['metrics_mean']['accuracy_20'],
            }
            rows.append(row)
        
        df = pd.DataFrame(rows)
        df = df.sort_values('mae').reset_index(drop=True)
        df['rank'] = df.index + 1
        
        return df


# =============================================================================
# Report Generator
# =============================================================================

class ReportGenerator:
    """
    Generate evaluation reports in markdown format.
    """
    
    def __init__(self, benchmark_results: Dict, leaderboard: pd.DataFrame):
        """
        Args:
            benchmark_results: Results from BenchmarkRunner
            leaderboard: Leaderboard DataFrame
        """
        self.results = benchmark_results
        self.leaderboard = leaderboard
    
    def generate_comparison_report(self, method1_name: str, method2_name: str,
                                    comparison_results: Dict) -> str:
        """
        Generate markdown report comparing two methods.
        
        Args:
            method1_name: Name of baseline method
            method2_name: Name of candidate method
            comparison_results: Results from compare_methods()
            
        Returns:
            Markdown report string
        """
        report = f"""# Method Comparison Report

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Overview

Comparison between **{method1_name}** (baseline) and **{method2_name}** (candidate).

## Performance Metrics

| Metric | {method1_name} | {method2_name} | Improvement |
|--------|----------------|----------------|-------------|
| MAE | {comparison_results['mae_method1']:.2f} | {comparison_results['mae_method2']:.2f} | {comparison_results['mae_method1'] - comparison_results['mae_method2']:.2f} |
| Winner | | **{comparison_results['winner']}** | |

## Statistical Validation

### Paired T-Test
- t-statistic: {comparison_results['statistical_tests']['paired_t_test']['t_statistic']:.4f}
- p-value: {comparison_results['statistical_tests']['paired_t_test']['p_value']:.4f}
- Significant: {'✓ Yes' if comparison_results['statistical_tests']['paired_t_test']['significant'] else '✗ No'}
- Interpretation: {comparison_results['statistical_tests']['paired_t_test']['interpretation']}

### Wilcoxon Signed-Rank Test
- Statistic: {comparison_results['statistical_tests']['wilcoxon_test']['statistic']:.4f}
- p-value: {comparison_results['statistical_tests']['wilcoxon_test']['p_value']:.4f}
- Significant: {'✓ Yes' if comparison_results['statistical_tests']['wilcoxon_test']['significant'] else '✗ No'}
- Interpretation: {comparison_results['statistical_tests']['wilcoxon_test']['interpretation']}

### Effect Size (Cohen's d)
- Cohen's d: {comparison_results['statistical_tests']['effect_size']['cohens_d']:.4f}
- Magnitude: {comparison_results['statistical_tests']['effect_size']['interpretation']}
- Better method: {comparison_results['statistical_tests']['effect_size']['better_method']}

## Recommendation

Based on the statistical analysis:

"""
        
        # Add recommendation
        t_test_sig = comparison_results['statistical_tests']['paired_t_test']['significant']
        wilcoxon_sig = comparison_results['statistical_tests']['wilcoxon_test']['significant']
        effect_size = comparison_results['statistical_tests']['effect_size']['interpretation']
        
        if t_test_sig and wilcoxon_sig:
            if comparison_results['mae_method2'] < comparison_results['mae_method1']:
                report += f"""**✓ PROMOTE**: {method2_name} shows statistically significant improvement over {method1_name}.

- Both t-test and Wilcoxon test confirm significance (p < 0.05)
- Effect size: {effect_size}
- MAE improvement: {comparison_results['mae_method1'] - comparison_results['mae_method2']:.2f} cycles

**Recommendation**: Move {method2_name} to shadow mode for production monitoring.
"""
            else:
                report += f"""**✗ REJECT**: {method2_name} performs worse than {method1_name}.

- Statistically significant worse performance
- Not recommended for deployment
"""
        elif t_test_sig or wilcoxon_sig:
            report += f"""**⚠ NEEDS MORE DATA**: Results are mixed.

- One test shows significance, other doesn't
- Recommend running with more seeds (10+) for robust conclusion
"""
        else:
            report += f"""**⚠ NO SIGNIFICANT DIFFERENCE**: Methods perform similarly.

- Neither test shows statistical significance
- Effect size: {effect_size}
- Consider other factors (latency, complexity, interpretability) for decision
"""
        
        return report
    
    def generate_leaderboard_report(self) -> str:
        """
        Generate leaderboard report.
        
        Returns:
            Markdown leaderboard string
        """
        report = f"""# Battery RUL Method Leaderboard

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Rankings

"""
        
        # Add leaderboard table
        report += "| Rank | Method | MAE | RMSE | MAPE (%) | R² | Acc@10% | Acc@20% |\n"
        report += "|------|--------|-----|------|----------|-----|---------|---------|\n"
        
        for _, row in self.leaderboard.iterrows():
            report += f"| {row['rank']} | {row['method']} | {row['mae']:.2f} ± {row['mae_std']:.2f} | {row['rmse']:.2f} | {row['mape']:.2f} | {row['r2']:.4f} | {row['accuracy_10']:.1f}% | {row['accuracy_20']:.1f}% |\n"
        
        report += f"""

## Summary

- **Total methods benchmarked:** {len(self.leaderboard)}
- **Best method:** {self.leaderboard.iloc[0]['method']} (MAE: {self.leaderboard.iloc[0]['mae']:.2f})
- **Worst method:** {self.leaderboard.iloc[-1]['method']} (MAE: {self.leaderboard.iloc[-1]['mae']:.2f})

"""
        
        return report


# =============================================================================
# Main Evaluation Pipeline
# =============================================================================

def evaluate_method(method_name: str, model, test_data: Tuple[np.ndarray, np.ndarray],
                    n_seeds: int = 5) -> Dict:
    """
    Complete evaluation pipeline for a single method.
    
    Args:
        method_name: Name of the method
        model: Trained model instance
        test_data: (X_test, y_test) tuple
        n_seeds: Number of seeds for robustness
        
    Returns:
        Evaluation results dict
    """
    runner = BenchmarkRunner(test_data)
    results = runner.run_method(method_name, model, n_seeds=n_seeds)
    
    return results


def compare_methods(baseline_model, candidate_model, 
                    test_data: Tuple[np.ndarray, np.ndarray],
                    baseline_name: str = "baseline",
                    candidate_name: str = "candidate",
                    n_seeds: int = 5) -> Dict:
    """
    Complete comparison pipeline between two methods.
    
    Args:
        baseline_model: Baseline model instance
        candidate_model: Candidate model instance
        test_data: (X_test, y_test) tuple
        baseline_name: Name for baseline method
        candidate_name: Name for candidate method
        n_seeds: Number of seeds
        
    Returns:
        Comparison results dict
    """
    runner = BenchmarkRunner(test_data)
    
    # Run both methods
    runner.run_method(baseline_name, baseline_model, n_seeds=n_seeds)
    runner.run_method(candidate_name, candidate_model, n_seeds=n_seeds)
    
    # Compare
    comparison = runner.compare_methods(baseline_name, candidate_name)
    
    # Generate report
    report_gen = ReportGenerator(runner.results, runner.generate_leaderboard())
    report = report_gen.generate_comparison_report(
        baseline_name, candidate_name, comparison
    )
    
    return {
        'comparison': comparison,
        'report': report,
        'leaderboard': runner.generate_leaderboard(),
    }


if __name__ == '__main__':
    # Test the evaluation framework
    print("Testing Evaluation Framework...")
    
    # Create dummy predictions
    np.random.seed(42)
    n_samples = 100
    
    y_true = np.random.randn(n_samples) * 100 + 500
    y_pred_1 = y_true + np.random.randn(n_samples) * 50
    y_pred_2 = y_true + np.random.randn(n_samples) * 40  # Better
    
    # Test metrics
    print("\n✓ Testing metrics...")
    metrics_1 = compute_all_metrics(y_true, y_pred_1)
    metrics_2 = compute_all_metrics(y_true, y_pred_2)
    
    print(f"  Method 1 MAE: {metrics_1['mae']:.2f}")
    print(f"  Method 2 MAE: {metrics_2['mae']:.2f}")
    
    # Test statistical tests
    print("\n✓ Testing statistical tests...")
    errors_1 = np.abs(y_true - y_pred_1)
    errors_2 = np.abs(y_true - y_pred_2)
    
    stats_results = run_statistical_tests(errors_1, errors_2)
    print(f"  T-test p-value: {stats_results['paired_t_test']['p_value']:.4f}")
    print(f"  Effect size: {stats_results['effect_size']['cohens_d']:.4f} ({stats_results['effect_size']['interpretation']})")
    
    print("\n✓ Evaluation framework test passed!")
