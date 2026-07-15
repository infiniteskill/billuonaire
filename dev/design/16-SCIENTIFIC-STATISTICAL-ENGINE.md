# 🔬 SCIENTIFIC STATISTICAL ENGINE

> **Purpose**: Mathematical foundation for sniper-precision detection
> **Philosophy**: Every pattern is mathematically quantifiable
> **Goal**: Self-sufficient, self-learning, self-evolving probabilistic system

---

## 🎯 THE SCIENTIFIC APPROACH

```
╔═══════════════════════════════════════════════════════════════════════╗
║                                                                        ║
║   "In God we trust. All others must bring data."                       ║
║                                         - W. Edwards Deming            ║
║                                                                        ║
║   Our system doesn't guess. It CALCULATES.                             ║
║   Our system doesn't hope. It PREDICTS.                                ║
║   Our system doesn't fail twice. It LEARNS.                            ║
║                                                                        ║
╚═══════════════════════════════════════════════════════════════════════╝
```

---

# PART 1: 📊 PROBABILISTIC DECISION TREE

## Not Binary → Probabilistic

Traditional decision trees: `if condition → yes/no`
Our approach: `if condition → probability distribution`

```python
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional
from decimal import Decimal
import numpy as np
from scipy import stats

@dataclass
class ProbabilisticNode:
    """A node that outputs probabilities, not binary decisions"""
    id: str
    condition_type: str  # "threshold", "distribution", "bayesian", "ml"
    
    # For threshold conditions
    threshold: Optional[float] = None
    learned_threshold: Optional[float] = None  # Updated by learning
    
    # For distribution conditions
    distribution: Optional[stats.rv_continuous] = None
    
    # Probability outputs (not just true/false)
    output_probabilities: Dict[str, float] = field(default_factory=dict)
    # Example: {"BULLISH": 0.65, "BEARISH": 0.25, "NEUTRAL": 0.10}
    
    # Confidence in this node's output
    confidence: float = 0.5
    
    # Learning statistics
    total_evaluations: int = 0
    correct_predictions: int = 0
    bayesian_prior: Dict[str, float] = field(default_factory=dict)
    
    def evaluate(self, value: float, context: Dict) -> Dict[str, float]:
        """
        Evaluate condition and return probability distribution
        NOT a binary yes/no!
        """
        if self.condition_type == "threshold":
            return self._evaluate_threshold(value)
        elif self.condition_type == "distribution":
            return self._evaluate_distribution(value)
        elif self.condition_type == "bayesian":
            return self._evaluate_bayesian(value, context)
        else:
            return self.output_probabilities
    
    def _evaluate_threshold(self, value: float) -> Dict[str, float]:
        """
        Instead of: value > threshold → True
        We do: value > threshold → probability based on HOW MUCH above
        """
        threshold = self.learned_threshold or self.threshold
        
        if threshold is None:
            return {"UNCERTAIN": 1.0}
        
        # Calculate distance from threshold
        distance = value - threshold
        
        # Convert to probability using sigmoid
        # The further above threshold, the higher probability
        sigmoid = 1 / (1 + np.exp(-distance * 0.1))
        
        return {
            "ABOVE": sigmoid,
            "BELOW": 1 - sigmoid
        }
    
    def _evaluate_distribution(self, value: float) -> Dict[str, float]:
        """
        Compare value against learned distribution
        """
        if self.distribution is None:
            return {"UNCERTAIN": 1.0}
        
        # Get percentile in distribution
        percentile = self.distribution.cdf(value)
        
        return {
            "EXTREME_LOW": max(0, 0.1 - percentile) * 10,
            "LOW": max(0, min(percentile, 0.25)) * 4,
            "NORMAL": 1 - abs(percentile - 0.5) * 2,
            "HIGH": max(0, min(percentile - 0.75, 0.25)) * 4,
            "EXTREME_HIGH": max(0, percentile - 0.9) * 10
        }
    
    def _evaluate_bayesian(self, value: float, context: Dict) -> Dict[str, float]:
        """
        Use Bayesian inference to update probabilities based on evidence
        """
        # Start with prior
        posterior = self.bayesian_prior.copy()
        
        # Update based on evidence
        for evidence_key, evidence_value in context.items():
            if evidence_key in self.likelihood_tables:
                likelihoods = self.likelihood_tables[evidence_key].get(evidence_value, {})
                
                # Bayes: P(H|E) = P(E|H) * P(H) / P(E)
                total = sum(
                    likelihoods.get(h, 0.1) * posterior.get(h, 0.1)
                    for h in posterior
                )
                
                for hypothesis in posterior:
                    likelihood = likelihoods.get(hypothesis, 0.1)
                    posterior[hypothesis] = (likelihood * posterior[hypothesis]) / total
        
        return posterior
    
    def update_from_outcome(self, predicted: str, actual: str, context: Dict):
        """Learn from outcome - Bayesian update"""
        self.total_evaluations += 1
        
        if predicted == actual:
            self.correct_predictions += 1
            # Strengthen prior for correct prediction
            self.bayesian_prior[predicted] = self.bayesian_prior.get(predicted, 0.5) * 1.02
        else:
            # Weaken prior for incorrect, strengthen actual
            self.bayesian_prior[predicted] = self.bayesian_prior.get(predicted, 0.5) * 0.98
            self.bayesian_prior[actual] = self.bayesian_prior.get(actual, 0.5) * 1.02
        
        # Normalize
        total = sum(self.bayesian_prior.values())
        self.bayesian_prior = {k: v/total for k, v in self.bayesian_prior.items()}
        
        # Update confidence based on accuracy
        self.confidence = self.correct_predictions / self.total_evaluations


class ProbabilisticDecisionTree:
    """
    A decision tree where every path computes probabilities,
    not binary yes/no decisions.
    
    Final output is a probability distribution:
    {"BULLISH": 0.62, "BEARISH": 0.28, "NEUTRAL": 0.10}
    """
    
    def __init__(self):
        self.nodes: Dict[str, ProbabilisticNode] = {}
        self.root_node_id: str = "root"
        self.version: int = 1
    
    def evaluate(self, factors: Dict) -> Dict[str, float]:
        """
        Traverse tree, accumulating probabilities at each node.
        
        Unlike binary trees that take ONE path,
        we take ALL paths weighted by probability.
        """
        # Start with uniform prior
        final_probs = {"BULLISH": 0.33, "BEARISH": 0.33, "NEUTRAL": 0.34}
        
        # Traverse all paths, weighted by probability
        path_results = self._traverse_all_paths(self.root_node_id, factors, 1.0)
        
        # Aggregate results from all paths
        for path_prob, path_result in path_results:
            for outcome, prob in path_result.items():
                if outcome in final_probs:
                    final_probs[outcome] = (
                        final_probs[outcome] * 0.5 + 
                        prob * path_prob * 0.5
                    )
        
        # Normalize
        total = sum(final_probs.values())
        return {k: v/total for k, v in final_probs.items()}
    
    def _traverse_all_paths(
        self, 
        node_id: str, 
        factors: Dict, 
        cumulative_prob: float
    ) -> List[Tuple[float, Dict[str, float]]]:
        """Recursively traverse all paths with their probabilities"""
        
        if node_id not in self.nodes:
            return [(cumulative_prob, {"UNCERTAIN": 1.0})]
        
        node = self.nodes[node_id]
        
        # Evaluate this node
        value = self._get_factor_value(factors, node.condition_type)
        node_result = node.evaluate(value, factors)
        
        results = []
        
        # Follow all branches weighted by probability
        for branch, prob in node_result.items():
            if prob > 0.01:  # Prune very low probability paths
                next_node = self._get_next_node(node_id, branch)
                
                if next_node in ["BULLISH", "BEARISH", "NEUTRAL"]:
                    # Terminal node
                    results.append((cumulative_prob * prob, {next_node: 1.0}))
                elif next_node:
                    # Continue traversal
                    results.extend(
                        self._traverse_all_paths(next_node, factors, cumulative_prob * prob)
                    )
        
        return results
```

---

# PART 2: 📈 CURVATURE & PATTERN ANALYSIS

## Mathematical Pattern Detection

```python
import numpy as np
from scipy import signal
from scipy.fft import fft, ifft
from scipy.optimize import curve_fit
from typing import List, Tuple
from dataclasses import dataclass
from enum import Enum

class CurvePattern(Enum):
    # Directional
    CONTINUOUS_UP = "CONTINUOUS_UP"        # Steady upward curve
    CONTINUOUS_DOWN = "CONTINUOUS_DOWN"    # Steady downward curve
    
    # U-Shaped
    U_SHAPE = "U_SHAPE"                    # Down then up (bullish reversal)
    INVERTED_U = "INVERTED_U"              # Up then down (bearish reversal)
    
    # Oscillating
    SINUSOIDAL = "SINUSOIDAL"              # Regular oscillation
    DAMPED_SINE = "DAMPED_SINE"            # Decreasing oscillation
    
    # Chaotic
    RANDOM_WALK = "RANDOM_WALK"            # No pattern (danger!)
    WHIPSAW = "WHIPSAW"                    # Rapid reversals (trap!)
    
    # Complex
    HEAD_SHOULDERS = "HEAD_SHOULDERS"      # Triple peak pattern
    DOUBLE_TOP = "DOUBLE_TOP"              # Two peaks, similar height
    DOUBLE_BOTTOM = "DOUBLE_BOTTOM"        # Two valleys
    
    # Accumulation
    RANGE_BOUND = "RANGE_BOUND"            # Trading range
    COMPRESSION = "COMPRESSION"            # Decreasing range (breakout coming)


@dataclass
class CurvatureAnalysis:
    """Complete curvature analysis of price data"""
    
    # Primary pattern detected
    pattern: CurvePattern
    confidence: float
    
    # Mathematical properties
    first_derivative_avg: float    # Trend direction
    second_derivative_avg: float   # Acceleration
    curvature: float               # How curved
    inflection_points: List[int]   # Where direction changes
    
    # Fourier analysis
    dominant_frequency: float      # Main cycle length
    frequency_power: float         # How strong is the cycle
    noise_ratio: float             # Signal to noise
    
    # Statistical properties
    mean_reversion_strength: float  # How quickly returns to mean
    hurst_exponent: float          # Trend persistence (>0.5 = trending)
    
    # Trap indicators
    trap_probability: float        # Probability this is a trap pattern
    trap_type: Optional[str]       # What kind of trap


class CurvatureAnalyzer:
    """
    Analyze price curves using calculus, Fourier analysis, 
    and statistical methods.
    """
    
    def __init__(self):
        self.pattern_library = self._build_pattern_library()
    
    def analyze(self, prices: List[float]) -> CurvatureAnalysis:
        """Complete curvature analysis"""
        
        prices = np.array(prices)
        n = len(prices)
        
        # 1. Calculate derivatives (trend and acceleration)
        first_deriv = np.gradient(prices)
        second_deriv = np.gradient(first_deriv)
        
        # 2. Calculate curvature
        # κ = |f''(x)| / (1 + f'(x)²)^(3/2)
        curvature = np.abs(second_deriv) / np.power(1 + first_deriv**2, 1.5)
        avg_curvature = np.mean(curvature)
        
        # 3. Find inflection points (where second derivative changes sign)
        inflection_points = self._find_inflection_points(second_deriv)
        
        # 4. Fourier analysis
        freq, power, dominant_freq, noise_ratio = self._fourier_analysis(prices)
        
        # 5. Calculate Hurst exponent (trend persistence)
        hurst = self._calculate_hurst(prices)
        
        # 6. Mean reversion strength
        mean_reversion = self._calculate_mean_reversion(prices)
        
        # 7. Detect pattern
        pattern, pattern_confidence = self._detect_pattern(
            prices, first_deriv, second_deriv, 
            inflection_points, dominant_freq, hurst
        )
        
        # 8. Calculate trap probability
        trap_prob, trap_type = self._calculate_trap_probability(
            pattern, prices, inflection_points, noise_ratio
        )
        
        return CurvatureAnalysis(
            pattern=pattern,
            confidence=pattern_confidence,
            first_derivative_avg=float(np.mean(first_deriv)),
            second_derivative_avg=float(np.mean(second_deriv)),
            curvature=float(avg_curvature),
            inflection_points=inflection_points,
            dominant_frequency=dominant_freq,
            frequency_power=power,
            noise_ratio=noise_ratio,
            mean_reversion_strength=mean_reversion,
            hurst_exponent=hurst,
            trap_probability=trap_prob,
            trap_type=trap_type
        )
    
    def _find_inflection_points(self, second_deriv: np.ndarray) -> List[int]:
        """Find points where curvature changes sign (direction changes)"""
        inflections = []
        
        for i in range(1, len(second_deriv)):
            if second_deriv[i-1] * second_deriv[i] < 0:  # Sign change
                inflections.append(i)
        
        return inflections
    
    def _fourier_analysis(
        self, 
        prices: np.ndarray
    ) -> Tuple[np.ndarray, float, float, float]:
        """
        Fourier analysis to detect cyclical patterns.
        
        Returns:
        - frequencies
        - power of dominant frequency
        - dominant frequency (cycle length)
        - noise ratio (signal quality)
        """
        n = len(prices)
        
        # Detrend (remove linear trend for better frequency analysis)
        detrended = signal.detrend(prices)
        
        # FFT
        fft_result = fft(detrended)
        power_spectrum = np.abs(fft_result[:n//2])**2
        frequencies = np.fft.fftfreq(n)[:n//2]
        
        # Find dominant frequency
        dominant_idx = np.argmax(power_spectrum[1:]) + 1  # Skip DC component
        dominant_freq = frequencies[dominant_idx]
        dominant_power = power_spectrum[dominant_idx]
        
        # Calculate signal-to-noise
        total_power = np.sum(power_spectrum)
        noise_power = total_power - dominant_power
        noise_ratio = noise_power / total_power if total_power > 0 else 1.0
        
        return frequencies, float(dominant_power), float(1/dominant_freq if dominant_freq > 0 else 0), float(noise_ratio)
    
    def _calculate_hurst(self, prices: np.ndarray, max_lag: int = 20) -> float:
        """
        Calculate Hurst exponent to measure trend persistence.
        
        H < 0.5: Mean-reverting (anti-persistent)
        H = 0.5: Random walk (no memory)
        H > 0.5: Trending (persistent)
        """
        lags = range(2, min(max_lag, len(prices)//2))
        
        if len(prices) < 10:
            return 0.5  # Not enough data
        
        # R/S analysis
        rs_values = []
        
        for lag in lags:
            rs = self._rs_statistic(prices, lag)
            rs_values.append(rs)
        
        if not rs_values or len(rs_values) < 3:
            return 0.5
        
        # Fit log-log regression
        log_lags = np.log(list(lags))
        log_rs = np.log(rs_values)
        
        # Linear regression: log(R/S) = H * log(n) + const
        slope, _ = np.polyfit(log_lags, log_rs, 1)
        
        return float(np.clip(slope, 0, 1))
    
    def _rs_statistic(self, prices: np.ndarray, lag: int) -> float:
        """Calculate R/S statistic for a given lag"""
        returns = np.diff(prices)
        
        if lag >= len(returns):
            return 1.0
        
        chunks = [returns[i:i+lag] for i in range(0, len(returns)-lag+1, lag)]
        
        rs_values = []
        for chunk in chunks:
            if len(chunk) < 2:
                continue
            
            mean = np.mean(chunk)
            std = np.std(chunk)
            
            if std == 0:
                continue
            
            cumsum = np.cumsum(chunk - mean)
            R = np.max(cumsum) - np.min(cumsum)
            rs_values.append(R / std)
        
        return np.mean(rs_values) if rs_values else 1.0
    
    def _calculate_mean_reversion(self, prices: np.ndarray) -> float:
        """
        Calculate mean reversion strength using Ornstein-Uhlenbeck process.
        Higher = faster mean reversion
        """
        if len(prices) < 10:
            return 0.5
        
        mean = np.mean(prices)
        deviations = prices - mean
        
        # Calculate how quickly price returns to mean
        returns = np.diff(deviations)
        
        # Regression: dX = theta * (mean - X) * dt
        # theta is mean reversion speed
        X = np.cov(returns[:-1], deviations[1:-1])
        
        if X[1, 1] != 0:
            theta = -X[0, 1] / X[1, 1]
        else:
            theta = 0
        
        # Normalize to 0-1 range
        return float(np.clip(theta, 0, 1))
    
    def _detect_pattern(
        self,
        prices: np.ndarray,
        first_deriv: np.ndarray,
        second_deriv: np.ndarray,
        inflections: List[int],
        dominant_freq: float,
        hurst: float
    ) -> Tuple[CurvePattern, float]:
        """Detect which pattern the prices follow"""
        
        n = len(prices)
        
        # 1. Check for continuous trend
        avg_first = np.mean(first_deriv)
        std_first = np.std(first_deriv)
        
        if avg_first > std_first * 0.5 and len(inflections) < 3:
            return CurvePattern.CONTINUOUS_UP, 0.8
        
        if avg_first < -std_first * 0.5 and len(inflections) < 3:
            return CurvePattern.CONTINUOUS_DOWN, 0.8
        
        # 2. Check for sinusoidal pattern
        if dominant_freq > 5 and dominant_freq < n/2:
            # Strong periodic component
            if hurst < 0.4:  # Mean-reverting confirms oscillation
                return CurvePattern.SINUSOIDAL, 0.75
        
        # 3. Check for U-shape or inverted U
        if len(inflections) == 1:
            mid = inflections[0]
            first_half_trend = np.mean(first_deriv[:mid])
            second_half_trend = np.mean(first_deriv[mid:])
            
            if first_half_trend < 0 and second_half_trend > 0:
                return CurvePattern.U_SHAPE, 0.8
            
            if first_half_trend > 0 and second_half_trend < 0:
                return CurvePattern.INVERTED_U, 0.8
        
        # 4. Check for whipsaw
        if len(inflections) > n / 5:  # Too many direction changes
            return CurvePattern.WHIPSAW, 0.7
        
        # 5. Check for range-bound
        price_range = np.max(prices) - np.min(prices)
        avg_range = np.mean([np.max(prices[i:i+10]) - np.min(prices[i:i+10]) 
                            for i in range(0, n-10, 5)])
        
        if price_range < avg_range * 3:
            return CurvePattern.RANGE_BOUND, 0.65
        
        # 6. Check for compression
        if len(inflections) > 2:
            ranges = []
            for i in range(len(inflections)-1):
                start, end = inflections[i], inflections[i+1]
                ranges.append(np.max(prices[start:end]) - np.min(prices[start:end]))
            
            if len(ranges) > 1 and ranges[-1] < ranges[0] * 0.5:
                return CurvePattern.COMPRESSION, 0.7
        
        # 7. Random walk
        if 0.45 < hurst < 0.55:
            return CurvePattern.RANDOM_WALK, 0.6
        
        return CurvePattern.RANDOM_WALK, 0.4
    
    def _calculate_trap_probability(
        self,
        pattern: CurvePattern,
        prices: np.ndarray,
        inflections: List[int],
        noise_ratio: float
    ) -> Tuple[float, Optional[str]]:
        """Calculate probability that current pattern is a trap"""
        
        trap_prob = 0.0
        trap_type = None
        
        # High trap probability patterns
        if pattern == CurvePattern.WHIPSAW:
            trap_prob = 0.85
            trap_type = "STOP_HUNT_MULTIPLE"
        
        elif pattern == CurvePattern.INVERTED_U:
            # Bull trap - goes up then reverses
            trap_prob = 0.7
            trap_type = "BULL_TRAP"
        
        elif pattern == CurvePattern.U_SHAPE:
            # Bear trap - goes down then reverses
            trap_prob = 0.7
            trap_type = "BEAR_TRAP"
        
        elif pattern == CurvePattern.RANDOM_WALK:
            # Unpredictable = danger
            trap_prob = 0.5
            trap_type = "RANDOM_HUNT"
        
        elif pattern == CurvePattern.SINUSOIDAL:
            # Oscillating - traps at extremes
            trap_prob = 0.4
            trap_type = "OSCILLATION_TRAP"
        
        # Adjust by noise ratio
        trap_prob = trap_prob * (0.5 + noise_ratio * 0.5)
        
        return trap_prob, trap_type
```

---

# PART 3: 🔮 FULL-DAY PROJECTION ENGINE

## Project Entire Day's Candles

```python
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime, time, timedelta
import numpy as np
from scipy import stats

@dataclass
class ProjectedCandle:
    """A projected candle with confidence bands"""
    timestamp: datetime
    
    # Most likely values
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    
    # Confidence bands
    high_upper: Decimal    # Upper band for high
    high_lower: Decimal    # Lower band for high
    low_upper: Decimal     # Upper band for low
    low_lower: Decimal     # Lower band for low
    close_upper: Decimal
    close_lower: Decimal
    
    # Probabilities
    is_bullish_prob: float
    is_trend_continuation_prob: float
    is_reversal_prob: float
    
    # Confidence
    overall_confidence: float


@dataclass
class DayProjection:
    """Full day's projected candles"""
    symbol: str
    date: datetime
    timeframe: str
    
    # All projected candles for the day
    candles: List[ProjectedCandle]
    
    # Summary
    projected_day_high: Decimal
    projected_day_low: Decimal
    projected_day_close: Decimal
    projected_direction: str  # BULLISH, BEARISH, NEUTRAL
    
    # Key events
    expected_sweep_times: List[time]
    expected_reversal_times: List[time]
    high_risk_periods: List[Tuple[time, time]]
    
    # Confidence
    overall_confidence: float
    confidence_decay_per_hour: float


class FullDayProjector:
    """
    Project entire day's candles using:
    1. Historical patterns for same day/time
    2. Current market context
    3. Statistical modeling
    4. Monte Carlo simulation
    """
    
    def __init__(self, historical_db, markov_engine, curvature_analyzer):
        self.history = historical_db
        self.markov = markov_engine
        self.curvature = curvature_analyzer
        
        # Market timing (Indian market)
        self.market_open = time(9, 15)
        self.market_close = time(15, 30)
    
    def project_full_day(
        self,
        symbol: str,
        date: datetime,
        timeframe: str,
        current_candles: List[Candle],  # Data we have so far
        context: Dict
    ) -> DayProjection:
        """Project remaining candles for the day"""
        
        # 1. Analyze current state
        current_analysis = self._analyze_current_state(current_candles)
        
        # 2. Get historical patterns for this time
        historical_patterns = self._get_historical_patterns(
            symbol, date.weekday(), len(current_candles), timeframe
        )
        
        # 3. Calculate phase probabilities
        phase_probs = self._calculate_phase_probabilities(
            current_analysis, context
        )
        
        # 4. Generate projected candles
        projected_candles = self._generate_projections(
            current_candles,
            historical_patterns,
            phase_probs,
            timeframe,
            date
        )
        
        # 5. Calculate day summary
        summary = self._calculate_day_summary(projected_candles, current_candles)
        
        # 6. Identify key times
        sweep_times = self._identify_sweep_times(projected_candles)
        reversal_times = self._identify_reversal_times(projected_candles)
        high_risk = self._identify_high_risk_periods(projected_candles)
        
        return DayProjection(
            symbol=symbol,
            date=date,
            timeframe=timeframe,
            candles=projected_candles,
            projected_day_high=summary['high'],
            projected_day_low=summary['low'],
            projected_day_close=summary['close'],
            projected_direction=summary['direction'],
            expected_sweep_times=sweep_times,
            expected_reversal_times=reversal_times,
            high_risk_periods=high_risk,
            overall_confidence=summary['confidence'],
            confidence_decay_per_hour=0.05
        )
    
    def _generate_projections(
        self,
        current_candles: List[Candle],
        historical_patterns: List[Dict],
        phase_probs: Dict,
        timeframe: str,
        date: datetime
    ) -> List[ProjectedCandle]:
        """Generate projected candles for rest of day"""
        
        projected = []
        
        # Determine remaining candles
        candles_per_day = self._get_candles_per_day(timeframe)
        remaining = candles_per_day - len(current_candles)
        
        if remaining <= 0:
            return []
        
        # Get last known state
        last_candle = current_candles[-1]
        current_price = float(last_candle.close)
        
        # Calculate volatility from current data
        atr = self._calculate_atr(current_candles)
        
        # Get current curvature
        prices = [float(c.close) for c in current_candles]
        curve_analysis = self.curvature.analyze(prices)
        
        # Generate each candle
        for i in range(remaining):
            candle_index = len(current_candles) + i
            candle_time = self._get_candle_time(date, candle_index, timeframe)
            
            # Get historical distribution for this candle index
            hist_dist = self._get_historical_distribution(
                historical_patterns, candle_index
            )
            
            # Get Markov prediction
            markov_pred = self.markov.predict_next(
                current_price, 
                curve_analysis.pattern.value,
                candle_time.hour
            )
            
            # Monte Carlo simulation
            mc_result = self._monte_carlo_candle(
                current_price, atr, hist_dist, markov_pred, 
                phase_probs, candle_time
            )
            
            # Create projected candle
            proj_candle = ProjectedCandle(
                timestamp=candle_time,
                open=Decimal(str(mc_result['open'])),
                high=Decimal(str(mc_result['high'])),
                low=Decimal(str(mc_result['low'])),
                close=Decimal(str(mc_result['close'])),
                high_upper=Decimal(str(mc_result['high_upper'])),
                high_lower=Decimal(str(mc_result['high_lower'])),
                low_upper=Decimal(str(mc_result['low_upper'])),
                low_lower=Decimal(str(mc_result['low_lower'])),
                close_upper=Decimal(str(mc_result['close_upper'])),
                close_lower=Decimal(str(mc_result['close_lower'])),
                is_bullish_prob=mc_result['bullish_prob'],
                is_trend_continuation_prob=mc_result['continuation_prob'],
                is_reversal_prob=mc_result['reversal_prob'],
                overall_confidence=mc_result['confidence']
            )
            
            projected.append(proj_candle)
            current_price = float(proj_candle.close)
        
        return projected
    
    def _monte_carlo_candle(
        self,
        current_price: float,
        atr: float,
        historical_dist: Dict,
        markov_pred: Dict,
        phase_probs: Dict,
        candle_time: datetime,
        n_simulations: int = 1000
    ) -> Dict:
        """
        Monte Carlo simulation for single candle.
        Run 1000 simulations, return distribution.
        """
        
        results = {
            'opens': [], 'highs': [], 'lows': [], 'closes': [],
            'bullish': 0
        }
        
        for _ in range(n_simulations):
            # Sample from distributions
            
            # Open: usually near previous close with some gap
            gap = np.random.normal(0, atr * 0.1)
            sim_open = current_price + gap
            
            # Direction influenced by Markov + phase + history
            bullish_prob = (
                markov_pred.get('bullish', 0.5) * 0.4 +
                historical_dist.get('bullish_prob', 0.5) * 0.3 +
                phase_probs.get('bullish', 0.5) * 0.3
            )
            
            is_bullish = np.random.random() < bullish_prob
            
            # Body size from historical distribution
            body_size = np.random.lognormal(
                np.log(atr * 0.3),
                0.5
            )
            
            # Wicks
            upper_wick = np.random.exponential(atr * 0.2)
            lower_wick = np.random.exponential(atr * 0.2)
            
            if is_bullish:
                sim_close = sim_open + body_size
                sim_high = sim_close + upper_wick
                sim_low = sim_open - lower_wick
                results['bullish'] += 1
            else:
                sim_close = sim_open - body_size
                sim_high = sim_open + upper_wick
                sim_low = sim_close - lower_wick
            
            results['opens'].append(sim_open)
            results['highs'].append(sim_high)
            results['lows'].append(sim_low)
            results['closes'].append(sim_close)
        
        # Calculate percentiles
        opens = np.array(results['opens'])
        highs = np.array(results['highs'])
        lows = np.array(results['lows'])
        closes = np.array(results['closes'])
        
        # Confidence decays with time
        hours_ahead = (candle_time.hour - 9) + (candle_time.minute / 60)
        confidence = max(0.3, 0.9 - hours_ahead * 0.05)
        
        return {
            'open': np.median(opens),
            'high': np.median(highs),
            'low': np.median(lows),
            'close': np.median(closes),
            
            'high_upper': np.percentile(highs, 90),
            'high_lower': np.percentile(highs, 10),
            'low_upper': np.percentile(lows, 90),
            'low_lower': np.percentile(lows, 10),
            'close_upper': np.percentile(closes, 75),
            'close_lower': np.percentile(closes, 25),
            
            'bullish_prob': results['bullish'] / n_simulations,
            'continuation_prob': 0.6,  # Would be calculated
            'reversal_prob': 0.2,
            'confidence': confidence
        }
    
    def _get_candles_per_day(self, timeframe: str) -> int:
        """Get number of candles in a trading day"""
        minutes_map = {
            '1m': 1, '5m': 5, '15m': 15, '30m': 30, '1h': 60
        }
        
        minutes = minutes_map.get(timeframe, 15)
        trading_minutes = 375  # 9:15 to 15:30
        
        return trading_minutes // minutes
    
    def _calculate_atr(self, candles: List[Candle], period: int = 14) -> float:
        """Calculate ATR from candles"""
        if len(candles) < period + 1:
            # Default if not enough data
            return float(candles[-1].high - candles[-1].low)
        
        true_ranges = []
        for i in range(1, len(candles)):
            high = float(candles[i].high)
            low = float(candles[i].low)
            prev_close = float(candles[i-1].close)
            
            tr = max(
                high - low,
                abs(high - prev_close),
                abs(low - prev_close)
            )
            true_ranges.append(tr)
        
        return sum(true_ranges[-period:]) / period
```

---

# PART 4: ⏰ TIMEFRAME-ADAPTIVE CALCULATIONS

## Any Duration, Any Timeframe

```python
from typing import Union, Tuple
from decimal import Decimal
from datetime import datetime, timedelta

class TimeframeAdapter:
    """
    Adapt calculations to ANY timeframe.
    Whether 1-minute or monthly data, calculations scale properly.
    """
    
    TIMEFRAME_MINUTES = {
        '1m': 1, '3m': 3, '5m': 5, '15m': 15, '30m': 30,
        '1h': 60, '2h': 120, '4h': 240,
        '1d': 1440, '1w': 10080, '1M': 43200
    }
    
    def __init__(self, base_timeframe: str = '15m'):
        self.base_tf = base_timeframe
        self.base_minutes = self.TIMEFRAME_MINUTES[base_timeframe]
    
    def scale_value(
        self, 
        value: float, 
        from_tf: str, 
        to_tf: str,
        scale_type: str = 'linear'
    ) -> float:
        """
        Scale a value from one timeframe to another.
        
        Example: ATR of 50 on 15m ≈ ATR of 100 on 1h
        """
        from_mins = self.TIMEFRAME_MINUTES[from_tf]
        to_mins = self.TIMEFRAME_MINUTES[to_tf]
        
        ratio = to_mins / from_mins
        
        if scale_type == 'linear':
            return value * ratio
        elif scale_type == 'sqrt':
            # Volatility scales with sqrt of time
            return value * np.sqrt(ratio)
        elif scale_type == 'log':
            return value * np.log(ratio + 1)
        
        return value
    
    def scale_atr(self, atr: float, from_tf: str, to_tf: str) -> float:
        """ATR scales with square root of time"""
        return self.scale_value(atr, from_tf, to_tf, 'sqrt')
    
    def scale_probability(
        self, 
        prob: float, 
        from_tf: str, 
        to_tf: str
    ) -> float:
        """
        Scale probability for different timeframes.
        Short-term events less likely on higher timeframes.
        """
        from_mins = self.TIMEFRAME_MINUTES[from_tf]
        to_mins = self.TIMEFRAME_MINUTES[to_tf]
        
        if to_mins > from_mins:
            # Higher timeframe: reduce probability of single events
            ratio = from_mins / to_mins
            return prob * ratio
        else:
            # Lower timeframe: increase granularity
            return min(0.99, prob * (to_mins / from_mins))
    
    def calculate_lookback(self, days: int, timeframe: str) -> int:
        """Calculate number of candles for N days"""
        tf_mins = self.TIMEFRAME_MINUTES[timeframe]
        trading_mins_per_day = 375  # 9:15 to 15:30
        
        candles_per_day = trading_mins_per_day // tf_mins
        return candles_per_day * days
    
    def calculate_confidence_decay(
        self, 
        candles_ahead: int, 
        timeframe: str
    ) -> float:
        """
        Calculate confidence decay for projections.
        1 hour = 4 candles on 15m = different decay than 1h
        """
        tf_mins = self.TIMEFRAME_MINUTES[timeframe]
        hours_ahead = (candles_ahead * tf_mins) / 60
        
        # Exponential decay
        decay_rate = 0.1  # per hour
        return np.exp(-decay_rate * hours_ahead)
    
    def normalize_swing_strength(
        self, 
        strength: int, 
        timeframe: str
    ) -> int:
        """
        Normalize swing strength across timeframes.
        Swing(3) on 1h ≈ Swing(12) on 15m
        """
        tf_mins = self.TIMEFRAME_MINUTES[timeframe]
        base_mins = self.base_minutes
        
        ratio = tf_mins / base_mins
        return int(strength / ratio) if ratio > 1 else strength
    
    def get_kill_zone_candles(self, timeframe: str) -> Dict[str, Tuple[int, int]]:
        """
        Convert time-based kill zones to candle indices.
        """
        tf_mins = self.TIMEFRAME_MINUTES[timeframe]
        
        def time_to_candle(t: time) -> int:
            minutes_from_open = (t.hour - 9) * 60 + (t.minute - 15)
            return minutes_from_open // tf_mins
        
        return {
            'MORNING_HUNT': (
                time_to_candle(time(9, 15)),
                time_to_candle(time(10, 30))
            ),
            'EXECUTION_1': (
                time_to_candle(time(11, 0)),
                time_to_candle(time(12, 30))
            ),
            'LUNCH': (
                time_to_candle(time(12, 30)),
                time_to_candle(time(13, 30))
            ),
            'EXECUTION_2': (
                time_to_candle(time(14, 0)),
                time_to_candle(time(14, 45))
            ),
            'CLOSING': (
                time_to_candle(time(14, 45)),
                time_to_candle(time(15, 30))
            )
        }
```

---

# PART 5: 🧮 STATISTICAL TRAP DETECTION

## Bayesian Trap Probability

```python
class BayesianTrapDetector:
    """
    Use Bayesian inference to detect traps with statistical rigor.
    
    P(Trap | Evidence) = P(Evidence | Trap) * P(Trap) / P(Evidence)
    """
    
    def __init__(self):
        # Prior probabilities of traps
        self.trap_priors = {
            'STOP_HUNT': 0.3,      # 30% of moves are stop hunts
            'BULL_TRAP': 0.15,     # 15% of breakouts are traps
            'BEAR_TRAP': 0.15,
            'FAKEOUT': 0.2,
            'MANIPULATION': 0.4,   # 40% of morning moves are manipulation
        }
        
        # Likelihood tables: P(Evidence | Trap Type)
        self.likelihoods = {
            'quick_reversal': {
                'STOP_HUNT': 0.85,
                'BULL_TRAP': 0.75,
                'BEAR_TRAP': 0.75,
                'FAKEOUT': 0.9,
                'MANIPULATION': 0.6
            },
            'closed_opposite_side': {
                'STOP_HUNT': 0.9,
                'BULL_TRAP': 0.8,
                'BEAR_TRAP': 0.8,
                'FAKEOUT': 0.85,
                'MANIPULATION': 0.5
            },
            'during_kill_zone': {
                'STOP_HUNT': 0.8,
                'BULL_TRAP': 0.5,
                'BEAR_TRAP': 0.5,
                'FAKEOUT': 0.6,
                'MANIPULATION': 0.9
            },
            'volume_spike': {
                'STOP_HUNT': 0.7,
                'BULL_TRAP': 0.6,
                'BEAR_TRAP': 0.6,
                'FAKEOUT': 0.5,
                'MANIPULATION': 0.8
            },
            'breaks_key_level': {
                'STOP_HUNT': 0.95,
                'BULL_TRAP': 0.7,
                'BEAR_TRAP': 0.7,
                'FAKEOUT': 0.8,
                'MANIPULATION': 0.7
            }
        }
    
    def calculate_trap_probability(
        self,
        evidence: Dict[str, bool]
    ) -> Dict[str, float]:
        """
        Calculate posterior probability for each trap type given evidence.
        """
        
        # Start with priors
        posteriors = self.trap_priors.copy()
        
        # Update for each piece of evidence
        for evidence_type, is_present in evidence.items():
            if evidence_type not in self.likelihoods:
                continue
            
            for trap_type in posteriors:
                likelihood = self.likelihoods[evidence_type].get(trap_type, 0.1)
                
                if is_present:
                    # Evidence supports trap
                    posteriors[trap_type] *= likelihood
                else:
                    # Absence of evidence
                    posteriors[trap_type] *= (1 - likelihood * 0.5)
        
        # Normalize
        total = sum(posteriors.values())
        if total > 0:
            posteriors = {k: v/total for k, v in posteriors.items()}
        
        return posteriors
    
    def detect(
        self,
        candle: Candle,
        context: Dict,
        key_levels: List[Decimal]
    ) -> Tuple[bool, str, float]:
        """
        Detect if current candle is a trap.
        
        Returns: (is_trap, trap_type, probability)
        """
        
        # Collect evidence
        evidence = {
            'quick_reversal': self._check_quick_reversal(candle, context),
            'closed_opposite_side': self._check_closed_opposite(candle),
            'during_kill_zone': context.get('in_kill_zone', False),
            'volume_spike': self._check_volume_spike(candle, context),
            'breaks_key_level': self._check_breaks_level(candle, key_levels)
        }
        
        # Calculate posteriors
        posteriors = self.calculate_trap_probability(evidence)
        
        # Find highest probability trap
        max_trap = max(posteriors.items(), key=lambda x: x[1])
        
        is_trap = max_trap[1] > 0.6  # Threshold
        
        return is_trap, max_trap[0], max_trap[1]
    
    def update_from_outcome(self, trap_type: str, was_correct: bool):
        """Learn from outcomes to improve priors"""
        if was_correct:
            self.trap_priors[trap_type] *= 1.05
        else:
            self.trap_priors[trap_type] *= 0.95
        
        # Normalize
        total = sum(self.trap_priors.values())
        self.trap_priors = {k: v/total for k, v in self.trap_priors.items()}
```

---

# PART 6: 🎯 SNIPER PRECISION SYSTEM

## The Ultimate Decision Engine

```python
class SniperSystem:
    """
    The final decisionengine.
    
    Combines ALL analysis into a single, precise signal.
    
    "One shot, one kill. No second chances."
    """
    
    def __init__(
        self,
        prob_tree: ProbabilisticDecisionTree,
        curvature: CurvatureAnalyzer,
        projector: FullDayProjector,
        trap_detector: BayesianTrapDetector,
        timeframe_adapter: TimeframeAdapter
    ):
        self.tree = prob_tree
        self.curvature = curvature
        self.projector = projector
        self.trap = trap_detector
        self.tf_adapter = timeframe_adapter
        
        # Sniper thresholds - very conservative
        self.min_confidence = 0.70
        self.min_probability = 0.65
        self.max_trap_probability = 0.30
        self.min_risk_reward = 2.0
    
    def analyze(
        self,
        symbol: str,
        timeframe: str,
        candles: List[Candle],
        context: Dict
    ) -> Dict:
        """
        Complete sniper analysis.
        
        Returns signal ONLY if ALL conditions met.
        """
        
        # 1. Probabilistic tree evaluation
        tree_probs = self.tree.evaluate(context)
        
        # 2. Curvature analysis
        prices = [float(c.close) for c in candles]
        curve = self.curvature.analyze(prices)
        
        # 3. Full day projection
        projection = self.projector.project_full_day(
            symbol, datetime.now(), timeframe, candles, context
        )
        
        # 4. Trap detection
        is_trap, trap_type, trap_prob = self.trap.detect(
            candles[-1], context, context.get('key_levels', [])
        )
        
        # 5. Calculate sniper score
        sniper_score = self._calculate_sniper_score(
            tree_probs, curve, projection, trap_prob, context
        )
        
        # 6. Decision
        take_shot = self._should_take_shot(sniper_score, trap_prob)
        
        return {
            'take_shot': take_shot,
            'direction': max(tree_probs.items(), key=lambda x: x[1])[0],
            'confidence': sniper_score['overall'],
            
            # Components
            'tree_probabilities': tree_probs,
            'curvature_pattern': curve.pattern.value,
            'trap_analysis': {
                'is_trap': is_trap,
                'type': trap_type,
                'probability': trap_prob
            },
            'day_projection': {
                'direction': projection.projected_direction,
                'high': projection.projected_day_high,
                'low': projection.projected_day_low,
                'confidence': projection.overall_confidence
            },
            
            # Full analysis
            'sniper_score': sniper_score,
            
            # Reasoning for transparency
            'reasoning': self._build_reasoning(
                tree_probs, curve, projection, trap_prob, take_shot
            )
        }
    
    def _calculate_sniper_score(
        self,
        tree_probs: Dict,
        curve: CurvatureAnalysis,
        projection: DayProjection,
        trap_prob: float,
        context: Dict
    ) -> Dict:
        """Calculate comprehensive sniper score"""
        
        # Get best direction from tree
        best_dir = max(tree_probs.items(), key=lambda x: x[1])
        direction_score = best_dir[1]
        
        # Pattern score
        safe_patterns = [
            CurvePattern.CONTINUOUS_UP,
            CurvePattern.CONTINUOUS_DOWN,
            CurvePattern.U_SHAPE,
            CurvePattern.INVERTED_U
        ]
        pattern_score = 0.8 if curve.pattern in safe_patterns else 0.4
        pattern_score *= curve.confidence
        
        # Trap avoidance score
        trap_score = 1 - trap_prob
        
        # Projection alignment score
        proj_aligned = (
            (projection.projected_direction == 'BULLISH' and best_dir[0] == 'BULLISH') or
            (projection.projected_direction == 'BEARISH' and best_dir[0] == 'BEARISH')
        )
        projection_score = 0.9 if proj_aligned else 0.5
        projection_score *= projection.overall_confidence
        
        # Time safety score
        time_score = 1 - context.get('danger_level', 0.5)
        
        # Hurst exponent alignment (trend persistence)
        if curve.hurst_exponent > 0.6:  # Trending
            hurst_score = 0.8
        elif curve.hurst_exponent < 0.4:  # Mean-reverting
            hurst_score = 0.7  # Good for reversals
        else:
            hurst_score = 0.5  # Random
        
        # Overall: weighted average
        overall = (
            direction_score * 0.25 +
            pattern_score * 0.20 +
            trap_score * 0.20 +
            projection_score * 0.15 +
            time_score * 0.10 +
            hurst_score * 0.10
        )
        
        return {
            'overall': overall,
            'direction': direction_score,
            'pattern': pattern_score,
            'trap_avoidance': trap_score,
            'projection': projection_score,
            'time_safety': time_score,
            'trend_persistence': hurst_score
        }
    
    def _should_take_shot(self, score: Dict, trap_prob: float) -> bool:
        """
        Final decision: Take the shot or wait.
        
        Conservative approach - only shoot when VERY confident.
        """
        
        # All conditions must be met
        conditions = [
            score['overall'] >= self.min_confidence,
            score['direction'] >= self.min_probability,
            trap_prob <= self.max_trap_probability,
            score['time_safety'] >= 0.5,
            score['trap_avoidance'] >= 0.7
        ]
        
        return all(conditions)
    
    def _build_reasoning(
        self,
        tree_probs: Dict,
        curve: CurvatureAnalysis,
        projection: DayProjection,
        trap_prob: float,
        take_shot: bool
    ) -> List[str]:
        """Build human-readable reasoning"""
        
        reasons = []
        
        best_dir = max(tree_probs.items(), key=lambda x: x[1])
        reasons.append(f"Tree: {best_dir[0]} ({best_dir[1]:.0%})")
        reasons.append(f"Pattern: {curve.pattern.value} (conf: {curve.confidence:.0%})")
        reasons.append(f"Trap probability: {trap_prob:.0%}")
        reasons.append(f"Day projection: {projection.projected_direction}")
        reasons.append(f"Hurst: {curve.hurst_exponent:.2f} ({'trending' if curve.hurst_exponent > 0.5 else 'mean-reverting'})")
        
        if take_shot:
            reasons.append("✅ ALL CONDITIONS MET - TAKE SHOT")
        else:
            reasons.append("❌ CONDITIONS NOT MET - STAND DOWN")
        
        return reasons
```

---

## ✅ ACCEPTANCE CRITERIA

- [ ] Probabilistic decision tree outputs distributions, not binary
- [ ] Bayesian inference updates from every outcome
- [ ] Curvature analysis detects all pattern types
- [ ] Fourier analysis identifies cycles
- [ ] Hurst exponent measures trend persistence
- [ ] Full-day projection via Monte Carlo
- [ ] Timeframe-adaptive calculations
- [ ] Trap probability calculated with evidence
- [ ] Sniper system requires ALL conditions met
- [ ] Self-learning: Every outcome updates model
- [ ] Self-evolving: Tree structure changes over time
- [ ] Self-sufficient: No manual intervention needed

---

> **THE SNIPER PHILOSOPHY**
> 
> We don't take every shot.
> We take only the PERFECT shot.
> 
> We wait.
> We calculate.
> We verify.
> 
> When we shoot, we DON'T miss.
