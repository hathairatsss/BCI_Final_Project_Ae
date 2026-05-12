import logging
import numpy as np
from brainflow.data_filter import DataFilter, FilterTypes

def process_eeg_data(data, eeg_channels, sampling_rate):
    """
    Apply filters and calculate Attention Score (Beta / Alpha Ratio).
    Returns: attention_score, alpha_power, beta_power
    """
    if data.shape[1] < sampling_rate: 
        return 0.5, 0.0, 0.0 # Default score if not enough data yet
        
    # Average across all EEG channels to reduce noise (Averaging before PSD)
    ch_data = np.mean(data[eeg_channels, :], axis=0)
    
    # 1. 50Hz/60Hz Notch filter (Assuming 50Hz for Thailand)
    DataFilter.perform_bandstop(ch_data, sampling_rate, 48.0, 52.0, 2, FilterTypes.BUTTERWORTH.value, 0)
    
    # 2. Bandpass filter (1-45Hz) to keep Theta, Alpha, and Beta
    DataFilter.perform_bandpass(ch_data, sampling_rate, 1.0, 45.0, 2, FilterTypes.BUTTERWORTH.value, 0)
    
    # 3. Calculate Band Power
    # We need nfft, typically next power of 2 based on data length
    nfft = DataFilter.get_nearest_power_of_two(len(ch_data))
    if nfft > len(ch_data):
        nfft = nfft // 2
    
    # Check if data length is sufficient for nfft
    if nfft < 16 or len(ch_data) < nfft:
        return 0.5, 0.0, 0.0

    try:
        psd = DataFilter.get_psd_welch(ch_data, nfft, nfft // 2, sampling_rate, 0)
        
        theta_power = DataFilter.get_band_power(psd, 4.0, 8.0) # Theta (4-8Hz)
        alpha_power = DataFilter.get_band_power(psd, 8.0, 12.0)
        beta_power = DataFilter.get_band_power(psd, 13.0, 30.0)
        
        # ปรับสูตรการคำนวณ Ratio
        denominator = theta_power + alpha_power
        if denominator == 0:
            return 0.5, alpha_power, beta_power
            
        ratio = beta_power / denominator
        
        # Normalize to 0-1 range for the frontend (heuristic mapping)
        # We'll map [0.5, 2.5] -> [0, 1]
        attention_score = (ratio - 0.1) / 0.5
        return max(0.0, min(1.0, attention_score)), alpha_power, beta_power
        
    except Exception as e:
        logging.warning(f"Error in PSD calculation: {e}")
        return 0.5, 0.0, 0.0

def process_dashboard_data(data, eeg_channels, sampling_rate):
    """
    Process data for the debug dashboard.
    Returns:
        dict containing:
        - raw_data: {ch_index: [values]}
        - fft_data: {frequencies: [...], psd: {ch_index: [...]}}
        - metrics: {ch_index: {beta_alpha, beta_theta_alpha, one_over_alpha}}
        - avg_metrics: {beta_alpha, beta_theta_alpha, one_over_alpha}
    """
    result = {
        "raw_data": {},
        "fft_data": {"frequencies": [], "psd": {}},
        "metrics": {},
        "avg_metrics": {"beta_alpha": 0.0, "beta_theta_alpha": 0.0, "one_over_alpha": 0.0}
    }
    
    if data.shape[1] < sampling_rate:
        return result
        
    nfft = DataFilter.get_nearest_power_of_two(data.shape[1])
    if nfft > data.shape[1]:
        nfft = nfft // 2
        
    if nfft < 16 or data.shape[1] < nfft:
        return result

    sum_metrics = {"beta_alpha": 0.0, "beta_theta_alpha": 0.0, "one_over_alpha": 0.0}
    valid_channels = 0

    for i, ch in enumerate(eeg_channels):
        ch_name = f"Ch {i+1}"
        ch_data = np.copy(data[ch, :])
        
        # Filters
        DataFilter.perform_bandstop(ch_data, sampling_rate, 48.0, 52.0, 2, FilterTypes.BUTTERWORTH.value, 0)
        DataFilter.perform_bandpass(ch_data, sampling_rate, 1.0, 45.0, 2, FilterTypes.BUTTERWORTH.value, 0)
        
        # Take the latest 1250 points for raw visual (5 seconds) to match OpenBCI UI
        result["raw_data"][ch_name] = np.round(ch_data[-1250:], 2).tolist()
        
        try:
            psd = DataFilter.get_psd_welch(ch_data, nfft, nfft // 2, sampling_rate, 0)
            ampls, freqs = psd[0], psd[1]
            
            # Mask psd to 0-40Hz for visualization
            freq_mask = (freqs >= 0) & (freqs <= 40)
            
            if len(result["fft_data"]["frequencies"]) == 0:
                result["fft_data"]["frequencies"] = np.round(freqs[freq_mask], 2).tolist()
            
            result["fft_data"]["psd"][ch_name] = np.round(ampls[freq_mask], 4).tolist()
            
            theta = DataFilter.get_band_power(psd, 4.0, 8.0)
            alpha = DataFilter.get_band_power(psd, 8.0, 12.0)
            beta = DataFilter.get_band_power(psd, 13.0, 30.0)
            
            beta_alpha = beta / alpha if alpha > 0 else 0.0
            beta_theta_alpha = beta / (theta + alpha) if (theta + alpha) > 0 else 0.0
            one_over_alpha = 1.0 / alpha if alpha > 0 else 0.0
            
            # Calculate uVrms from the last 1 second (250 samples)
            rms_val = float(np.sqrt(np.mean(ch_data[-250:]**2)))
            
            result["metrics"][ch_name] = {
                "beta_alpha": float(np.round(beta_alpha, 3)),
                "beta_theta_alpha": float(np.round(beta_theta_alpha, 3)),
                "one_over_alpha": float(np.round(one_over_alpha, 3)),
                "rms": float(np.round(rms_val, 1))
            }
            
            sum_metrics["beta_alpha"] += beta_alpha
            sum_metrics["beta_theta_alpha"] += beta_theta_alpha
            sum_metrics["one_over_alpha"] += one_over_alpha
            valid_channels += 1
            
        except Exception as e:
            logging.warning(f"Error processing channel {ch_name} for dashboard: {e}")
            
    if valid_channels > 0:
        result["avg_metrics"]["beta_alpha"] = round(sum_metrics["beta_alpha"] / valid_channels, 4)
        result["avg_metrics"]["beta_theta_alpha"] = round(sum_metrics["beta_theta_alpha"] / valid_channels, 4)
        result["avg_metrics"]["one_over_alpha"] = round(sum_metrics["one_over_alpha"] / valid_channels, 4)
        
    return result
