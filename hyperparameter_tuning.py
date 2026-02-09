from ml_train import train_fasttext_model, evaluate_model

configs = [
    # {'lr': 0.5, 'epoch': 25, 'wordNgrams': 2, 'dim': 100},  # Current
    # {'lr': 0.3, 'epoch': 50, 'wordNgrams': 3, 'dim': 150},  # More epochs, larger
    # {'lr': 0.7, 'epoch': 30, 'wordNgrams': 2, 'dim': 100},  # Higher learning rate
    # {'lr': 0.5, 'epoch': 25, 'wordNgrams': 3, 'dim': 100},  # Trigrams
    {'lr': 15, 'epoch': 30, 'wordNgrams': 2, 'dim': 150},  # Trigrams
]

for i, config in enumerate(configs):
    print(f"\n=== Config {i+1} ===")
    print(config)
    train_fasttext_model('data/train.txt', f'models/test_{i}.bin', **config)
    evaluate_model(f'models/test_{i}.bin', 'data/test.txt')