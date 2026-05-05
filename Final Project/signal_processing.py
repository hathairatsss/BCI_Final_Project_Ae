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
        
    # We will process channel 1 (eeg_channels[0]) for the attention score as an example
    ch = eeg_channels[0]
    ch_data = data[ch, :]
    
    # 1. 50Hz/60Hz Notch filter (Assuming 50Hz for Thailand)
    DataFilter.perform_bandstop(ch_data, sampling_rate, 50.0, 4.0, 2, FilterTypes.BUTTERWORTH.value, 0)
    
    # 2. Bandpass filter (1-40Hz)
    DataFilter.perform_bandpass(ch_data, sampling_rate, 20.5, 39.0, 2, FilterTypes.BUTTERWORTH.value, 0)
    
    # 3. Calculate Band Power
    # We need nfft, typically next power of 2 based on data length
    nfft = DataFilter.get_nearest_power_of_two(len(ch_data))
    
    # Check if data length is sufficient for nfft
    if len(ch_data) < nfft:
        return 0.5, 0.0, 0.0

    try:
        psd = DataFilter.get_psd_welch(ch_data, nfft, nfft // 2, sampling_rate, 0)
        
        # Alpha (8-12Hz)
        alpha_power = DataFilter.get_band_power(psd, 8.0, 12.0)
        # Beta (13-30Hz)
        beta_power = DataFilter.get_band_power(psd, 13.0, 30.0)
        
        # Calculate ratio
        if alpha_power == 0:
            return 0.5, alpha_power, beta_power
            
        ratio = beta_power / alpha_power
        
        # Normalize to 0-1 range for the frontend (heuristic mapping)
        # We'll map [0.5, 2.5] -> [0, 1]
        attention_score = (ratio - 0.5) / 2.0
        return max(0.0, min(1.0, attention_score)), alpha_power, beta_power
        
    except Exception as e:
        logging.warning(f"Error in PSD calculation: {e}")
        return 0.5, 0.0, 0.0
