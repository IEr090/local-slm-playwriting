from unittest import TestCase

from anton.application.language import echoes, language_of, play_language


class PlayLanguageTest(TestCase):
    """Test naming the language the play is written in."""

    def test_takes_language_of_the_idea(self) -> None:
        """Name Russian for a Russian idea, English for an English one and by default."""
        self.assertEqual(play_language("Коммунальная квартира в Ленинграде, 1974 год."), "Russian")
        self.assertEqual(play_language("A lighthouse keeper dies."), "English")
        self.assertEqual(play_language(""), "English")

    def test_recognises_german(self) -> None:
        """Recognise German by its letters or its most common words."""
        self.assertEqual(language_of("Ein Theater in Wien und die Schauspieler"), "German")
        self.assertEqual(language_of("He would rather die than sell the house to the agent"), "English")


class EchoTest(TestCase):
    """Test recognising an answer that copies its prompt."""

    def test_finds_a_copied_passage(self) -> None:
        """Find six words in a row from the prompt, whatever their case and punctuation."""
        prompt = "- `what_happens`: Four to six sentences. Start with the time of day or how much time has passed."
        self.assertTrue(echoes("Four to six sentences. Start with the time of day.", prompt))
        self.assertFalse(echoes("At dawn Ava finds the will and hides it from her brother.", prompt))
        self.assertFalse(echoes("Утром Ава находит завещание и прячет его от брата.", prompt))
