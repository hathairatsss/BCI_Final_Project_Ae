import asyncio
import json
import logging
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from brainflow.board_shim import BoardIds
from bci_manager import BCIManager
from signal_processing import process_eeg_data, process_dashboard_data
from csv_logger import CSVLogger

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------- CONFIGURATION -----------------
STREAM_HZ = 10 # 10Hz to frontend

# Global components
bci_manager = BCIManager(board_id=BoardIds.CYTON_BOARD.value, serial_port='COM4')
csv_logger = CSVLogger()

# Global variable for attention score to be logged
current_attention_score = 0.5

@app.on_event("startup")
async def startup_event():
    if bci_manager.connect():
        csv_logger.start(bci_manager.eeg_channels)
        asyncio.create_task(bci_poll_loop())
    else:
        logging.error("Failed to initialize BCI Manager on startup.")

async def bci_poll_loop():
    global current_attention_score
    while True:
        if bci_manager.is_streaming:
            new_data = bci_manager.get_all_data()
            if new_data is not None and new_data.shape[1] > 0:
                # Write to CSV immediately with the latest known attention score
                csv_logger.log_data(
                    new_data, 
                    new_data.shape[1], 
                    bci_manager.get_timestamp_channel(), 
                    bci_manager.eeg_channels, 
                    current_attention_score
                )
                bci_manager.append_to_local_buffer(new_data)
        await asyncio.sleep(0.05) # Poll at 20Hz

@app.on_event("shutdown")
async def shutdown_event():
    bci_manager.disconnect()
    csv_logger.stop()

@app.websocket("/ws/attention")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    logging.warning("Frontend connected to WebSocket.")
    try:
        while True:
            global current_attention_score
            # Get a slightly larger window for processing PSD (e.g., last 2 seconds)
            window_data = bci_manager.get_recent_data(bci_manager.sampling_rate * 2) 
            
            if window_data is not None and window_data.shape[1] >= bci_manager.sampling_rate:
                attention_score, current_alpha, current_beta = process_eeg_data(
                    window_data, 
                    bci_manager.eeg_channels, 
                    bci_manager.sampling_rate
                )
                current_attention_score = attention_score
            else:
                attention_score = 0.5
                current_alpha = 0.0
                current_beta = 0.0
                
            # Send to frontend
            payload = {
                "attention_score": float(attention_score),
                "alpha": float(current_alpha),
                "beta": float(current_beta)
            }
            await websocket.send_text(json.dumps(payload))
            
            # Wait for next tick (10Hz)
            await asyncio.sleep(1.0 / STREAM_HZ)
            
    except WebSocketDisconnect:
        logging.warning("Frontend disconnected.")
    except Exception as e:
        logging.error(f"WebSocket Error: {e}")

@app.websocket("/ws/dashboard")
async def websocket_dashboard(websocket: WebSocket):
    await websocket.accept()
    logging.warning("Dashboard connected to WebSocket.")
    try:
        while True:
            # Use get_recent_data instead of get_all_data so we don't steal
            # data from the main game loop's CSV logger.
            if bci_manager.is_streaming:
                window_data = bci_manager.get_recent_data(bci_manager.sampling_rate * 5)
                if window_data is not None and window_data.shape[1] > 0:
                    dashboard_payload = process_dashboard_data(
                        window_data, 
                        bci_manager.eeg_channels, 
                        bci_manager.sampling_rate
                    )
                    await websocket.send_text(json.dumps(dashboard_payload))
                
            await asyncio.sleep(1.0 / 4) # 4Hz refresh rate
            
    except WebSocketDisconnect:
        logging.warning("Dashboard disconnected.")
    except Exception as e:
        logging.error(f"Dashboard WebSocket Error: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
