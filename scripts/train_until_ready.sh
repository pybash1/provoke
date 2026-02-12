#!/bin/bash

# Target precision 
TARGET_PRECISION=0.998
PRECISION=0

echo "🚀 Starting training loop to reach precision $TARGET_PRECISION..."

while true; do
    echo "--------------------------------------------------------"
    echo "⏳ Training model..."
    
    # Run the training script and capture its output
    OUTPUT=$(uv run python -m provoke.ml.trainer --train 2>&1)
    
    # Store output to a temporary file for better debugging if needed
    echo "$OUTPUT"
    
    # Extract precision using grep and awk
    # Expected line format: "Precision: 0.XXX"
    PRECISION=$(echo "$OUTPUT" | grep "Precision:" | awk '{print $2}')
    
    if [ -z "$PRECISION" ]; then
        echo "❌ Error: Could not extract precision from output."
        echo "Make sure 'uv run python -m provoke.ml.trainer --train' is working correctly."
        exit 1
    fi
    
    echo "🎯 Current Precision: $PRECISION"
    
    # Compare current precision with target precision
    # Since bash doesn't handle floating point comparisons natively, we use 'bc'
    IS_REACHED=$(echo "$PRECISION >= $TARGET_PRECISION" | bc -l)
    
    if [ "$IS_REACHED" -eq 1 ]; then
        echo "✅ SUCCESS: Target precision of $TARGET_PRECISION reached!"
        break
    else
        echo "🔄 Precision $PRECISION is below target $TARGET_PRECISION. Retraining..."
    fi
done
