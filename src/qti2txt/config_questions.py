from dataclasses import dataclass


@dataclass
class QTIConfig:
    """Configuration settings for QTI processing."""

    # Question types to process
    supported_question_types: list[str] | None = None

    # File settings
    default_csv_name: str = "question_details.csv"
    default_log_name: str = "qti2txt.log"
    temp_file_prefix: str = "qti2txt"

    def __post_init__(self):
        if self.supported_question_types is None:
            self.supported_question_types = [
                "multiple_choice_question",
                "true_false_question",
                "short_answer_question",
                "essay_question",
                "numerical_question",
                "matching_question",
                "multiple_answers_question",
                "fill_in_multiple_blanks_question",
                "text_only_question",
                "file_upload_question",
            ]


# Global config instance
question_config = QTIConfig()
