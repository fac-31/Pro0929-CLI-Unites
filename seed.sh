#!/bin/bash

# create_test_notes.sh - Creates 5 test notes for semantic search testing

echo "🚀 Creating 5 test notes..."
echo ""

# Note 1: About cats
echo "📝 Creating note 1: About cats..."
notes add "My Cat Story" --body "I have a fluffy orange cat named Whiskers. She loves to chase mice and play with yarn. Cats are wonderful pets and great companions." --tag "pets" --tag "animals"

sleep 1

# Note 2: About dogs
echo "📝 Creating note 2: About dogs..."
notes add "Dog Training Tips" --body "Training a puppy requires patience and consistency. Dogs respond well to positive reinforcement. Golden retrievers are especially easy to train and very loyal." --tag "pets" --tag "training"

sleep 1

# Note 3: About programming
echo "📝 Creating note 3: About programming..."
notes add "Python Best Practices" --body "Writing clean Python code involves following PEP 8 guidelines. Use meaningful variable names and write docstrings for all functions. Type hints improve code readability." --tag "programming" --tag "python"

sleep 1

# Note 4: About cooking
echo "📝 Creating note 4: About cooking..."
notes add "Pasta Recipe" --body "To make perfect pasta, use plenty of salted boiling water. Cook until al dente and save some pasta water for the sauce. Fresh basil and parmesan make any pasta dish better." --tag "cooking" --tag "recipe"

sleep 1

# Note 5: About travel
echo "📝 Creating note 5: About travel..."
notes add "Paris Travel Guide" --body "Paris is a beautiful city with amazing architecture. The Eiffel Tower is iconic but visit early to avoid crowds. French cafes serve the best croissants and coffee in the morning." --tag "travel" --tag "europe"

echo ""
echo "✅ Done! Created 5 test notes."
echo ""
echo "🔍 Try semantic search with:"
echo "  notes semantic-search \"feline pets\""
echo "  notes semantic-search \"canine companions\""
echo "  notes semantic-search \"coding in Python\""
echo "  notes semantic-search \"Italian food\""
echo "  notes semantic-search \"visiting France\""
