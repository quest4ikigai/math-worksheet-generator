import os
import unittest
from io import StringIO
from unittest.mock import patch
import random
from fpdf.enums import XPos, YPos

from run import MathWorksheetGenerator as Mg
from run import OUTPUT_SIZE_CONFIG
from run import build_incremented_filename
from run import main
from run import next_available_output_path
from run import parse_cli_args
from run import prompt_for_output_path
from run import resolve_output_path

class TestStringMethods(unittest.TestCase):

    def test_generate_question_addition(self):
        g = Mg(type_='+', max_number=9, question_count=10)
        question = g.generate_question()
        self.assertEqual(question[0] + question[2], question[3])

    def test_generate_question_subtraction(self):
        g = Mg(type_='-', max_number=9, question_count=10)
        question = g.generate_question()
        self.assertEqual(question[0] - question[2], question[3])
        # answer should be greater than 0
        self.assertGreaterEqual(question[3], 0)

    def test_generate_question_multiplication(self):
        g = Mg(type_='x', max_number=9, question_count=10)
        question = g.generate_question()
        self.assertEqual(question[0] * question[2], question[3])

    def test_generate_question_division(self):
        g = Mg(type_='/', max_number=9, question_count=10)
        question = g.generate_question()
        self.assertEqual(question[0] / question[2], question[3])

    def test_generate_question_unsupport_type_(self):
        g = Mg(type_='p', max_number=9, question_count=10)
        with self.assertRaisesRegex(RuntimeError, expected_regex=r"Question main_type p not supported"):
            g.generate_question()

    def test_get_list_of_questions_correct_count(self):
        g = Mg(type_='x', max_number=9, question_count=10)
        question_list = g.get_list_of_questions(g.question_count)
        self.assertEqual(len(question_list), g.question_count)

    def test_get_list_of_questions_calls_random_choice_for_mix(self):
        g = Mg(type_='mix', max_number=9, question_count=10)

        with patch('random.choice', wraps=random.choice) as mock_choice:
            g.get_list_of_questions(g.question_count)
        
        # random.choice should be called at least question_count times, or more when there are duplicates
        self.assertGreaterEqual(mock_choice.call_count, g.question_count)

    def test_make_question_page_page_count(self):
        g = Mg(type_='x', max_number=9, question_count=2)
        question_info = [[1, '+', 1, 2]] * g.question_count
        g.make_question_page(question_info)
        total_page = 1
        self.assertEqual(total_page, g.pdf.page)

    def test_make_question_page_uses_medium_capacity_without_reducing_first_page(self):
        g = Mg(type_='x', max_number=9, question_count=21)
        question_info = [[1, '+', 1, 2]] * g.question_count

        with patch.object(g, 'print_header_section') as mock_header, \
             patch.object(g, 'print_question_row') as mock_question_row, \
             patch.object(g, 'print_horizontal_separator') as mock_separator:
            g.make_question_page(question_info)

        self.assertEqual(2, g.pdf.page)
        self.assertEqual(2, mock_header.call_count)
        self.assertEqual(
            [(0, 5), (5, 5), (10, 5), (15, 5), (20, 1)],
            [(call.args[1], call.args[2]) for call in mock_question_row.call_args_list]
        )
        self.assertEqual(3, mock_separator.call_count)

    def test_make_question_page_small_keeps_second_page_offsets_aligned(self):
        g = Mg(type_='x', max_number=9, question_count=24, output_size='small')
        question_info = [[1, '+', 1, 2]] * g.question_count

        with patch.object(g, 'print_header_section'), \
             patch.object(g, 'print_question_row') as mock_question_row, \
             patch.object(g, 'print_horizontal_separator'):
            g.make_question_page(question_info)

        self.assertEqual(
            [(0, 6), (6, 6), (12, 6), (18, 6)],
            [(call.args[1], call.args[2]) for call in mock_question_row.call_args_list]
        )

    def test_output_size_configures_questions_per_page(self):
        for output_size, expected_questions, expected_columns, expected_default_count in (
            ('xsmall', 30, 6, 90),
            ('small', 24, 6, 72),
            ('medium', 20, 5, 80),
            ('large', 12, 4, 84),
            ('xlarge', 8, 4, 80),
        ):
            with self.subTest(output_size=output_size):
                g = Mg(type_='x', max_number=9, question_count=1, output_size=output_size)
                self.assertEqual(expected_questions, g.questions_per_page)
                self.assertEqual(expected_questions, OUTPUT_SIZE_CONFIG[output_size]['questions_per_page'])
                self.assertEqual(
                    expected_default_count,
                    OUTPUT_SIZE_CONFIG[output_size]['default_question_count']
                )
                self.assertEqual(expected_columns, g.num_x_cell)

    def test_print_header_section_places_score_on_right(self):
        g = Mg(type_='x', max_number=9, question_count=1)
        with patch.object(g.pdf, 'cell') as mock_cell, \
             patch.object(g.pdf, 'ln') as mock_ln:
            g.print_header_section()

        self.assertEqual('Name: ____________________    Date: ____________', mock_cell.call_args_list[0].kwargs['txt'])
        self.assertEqual(XPos.LEFT, mock_cell.call_args_list[0].kwargs['new_x'])
        self.assertEqual(YPos.TOP, mock_cell.call_args_list[0].kwargs['new_y'])
        self.assertEqual('Score: ________', mock_cell.call_args_list[1].kwargs['txt'])
        self.assertEqual('R', mock_cell.call_args_list[1].kwargs['align'])
        self.assertEqual(XPos.LMARGIN, mock_cell.call_args_list[1].kwargs['new_x'])
        self.assertEqual(YPos.NEXT, mock_cell.call_args_list[1].kwargs['new_y'])
        mock_ln.assert_called_once_with(g.header_gap)

    def test_print_question_row_keeps_only_bottom_answer_line_borders(self):
        g = Mg(type_='x', max_number=9, question_count=1)
        with patch.object(g.pdf, 'cell') as mock_cell, \
             patch.object(g.pdf, 'set_font'), \
             patch.object(g.pdf, 'ln'):
            g.print_question_row([[12, '+', 7, 19]], 0, 1)

        bordered_calls = []
        for call in mock_cell.call_args_list:
            if 'border' in call.kwargs:
                bordered_calls.append(call.kwargs['border'])

        self.assertEqual(['B', 'B'], bordered_calls)

    def test_factors_two_digits(self):
        g = Mg(type_='x', max_number=9, question_count=2)
        expect_factors = {1, 2, 4, 13, 26, 52}
        self.assertEqual(expect_factors, g.factors(52))

    def test_factors_three_digits(self):
        g = Mg(type_='x', max_number=9, question_count=2)
        expect_factors = {1, 2, 3, 4, 6, 12, 73, 146, 219, 292, 438, 876}
        self.assertEqual(expect_factors, g.factors(876))

    def test_division_helper_zero_input(self):
        g = Mg(type_='x', max_number=9, question_count=2)
        division_info = g.division_helper(0)
        self.assertNotEqual(0, division_info[0])

    def test_division_helper_divisor_not_equal_one_nor_dividend(self):
        g = Mg(type_='x', max_number=9, question_count=2)
        division_info = g.division_helper(876)
        self.assertNotEqual(1, division_info[0])
        self.assertNotEqual(division_info[2], division_info[0])

    def test_division_helper_divisor_answer_type_is_int(self):
        g = Mg(type_='x', max_number=9, question_count=2)
        division_info = g.division_helper(876)
        self.assertIs(type(division_info[2]), int)

    def test_parse_cli_args_help_option_outputs_usage(self):
        with patch('sys.stdout', new=StringIO()) as fake_stdout:
            with self.assertRaises(SystemExit) as context:
                parse_cli_args(['-h'])

        self.assertEqual(0, context.exception.code)
        output = fake_stdout.getvalue()
        self.assertIn('usage:', output)
        self.assertIn('[-h]', output)
        self.assertIn('--type', output)
        self.assertIn('--digits', output)
        self.assertIn('--question_count', output)
        self.assertIn('--output', output)
        self.assertIn('--title', output)
        self.assertIn('--output-size', output)

    def test_parse_cli_args_without_arguments_outputs_help(self):
        with patch('sys.stdout', new=StringIO()) as fake_stdout:
            with self.assertRaises(SystemExit) as context:
                parse_cli_args([])

        self.assertEqual(0, context.exception.code)
        output = fake_stdout.getvalue()
        self.assertIn('usage:', output)
        self.assertIn('Generate printable math practice worksheets as PDF files.', output)
        self.assertIn('[-h]', output)

    def test_resolve_output_path_uses_output_directory_for_plain_filename(self):
        self.assertEqual('output/worksheet.pdf', resolve_output_path('worksheet.pdf'))

    def test_resolve_output_path_preserves_explicit_directory(self):
        self.assertEqual(
            os.path.join('custom', 'worksheet.pdf'),
            resolve_output_path(os.path.join('custom', 'worksheet.pdf'))
        )

    def test_parse_cli_args_defaults_output_size_to_medium(self):
        args = parse_cli_args(['--type', '+'])
        self.assertEqual('medium', args.output_size)
        self.assertEqual(80, args.question_count)

    def test_parse_cli_args_uses_question_count_default_for_each_output_size(self):
        for output_size, expected_question_count in (
            ('xsmall', 90),
            ('small', 72),
            ('medium', 80),
            ('large', 84),
            ('xlarge', 80),
        ):
            with self.subTest(output_size=output_size):
                args = parse_cli_args(['--type', '+', '-os', output_size])
                self.assertEqual(expected_question_count, args.question_count)

    def test_parse_cli_args_accepts_output_size_alias(self):
        args = parse_cli_args(['--type', '+', '-os', 'xsmall'])
        self.assertEqual('xsmall', args.output_size)
        self.assertEqual(90, args.question_count)

    def test_parse_cli_args_preserves_explicit_question_count(self):
        args = parse_cli_args(['--type', '+', '-os', 'xsmall', '-q', '15'])
        self.assertEqual('xsmall', args.output_size)
        self.assertEqual(15, args.question_count)

    def test_build_incremented_filename_appends_number_before_extension(self):
        self.assertEqual(
            os.path.join('output', 'worksheet-2.pdf'),
            build_incremented_filename(os.path.join('output', 'worksheet.pdf'), 2)
        )

    def test_next_available_output_path_skips_existing_incremented_names(self):
        existing_files = {
            os.path.join('output', 'worksheet.pdf'),
            os.path.join('output', 'worksheet-1.pdf'),
            os.path.join('output', 'worksheet-2.pdf'),
        }
        self.assertEqual(
            os.path.join('output', 'worksheet-3.pdf'),
            next_available_output_path(
                os.path.join('output', 'worksheet.pdf'),
                exists_func=existing_files.__contains__,
            )
        )

    def test_prompt_for_output_path_returns_original_path_when_missing(self):
        self.assertEqual(
            os.path.join('output', 'worksheet.pdf'),
            prompt_for_output_path(
                'worksheet.pdf',
                exists_func=lambda _: False,
                input_func=lambda _: '',
                print_func=lambda _: None,
            )
        )

    def test_prompt_for_output_path_accepts_overwrite_choice(self):
        self.assertEqual(
            os.path.join('output', 'worksheet.pdf'),
            prompt_for_output_path(
                'worksheet.pdf',
                exists_func=lambda _: True,
                input_func=lambda _: 'o',
                print_func=lambda _: None,
            )
        )

    def test_prompt_for_output_path_aborts_on_abort_choice(self):
        with self.assertRaisesRegex(SystemExit, 'Aborted without overwriting'):
            prompt_for_output_path(
                'worksheet.pdf',
                exists_func=lambda _: True,
                input_func=lambda _: 'a',
                print_func=lambda _: None,
            )

    def test_prompt_for_output_path_can_change_name(self):
        responses = iter(['c', 'new-name.pdf'])
        self.assertEqual(
            os.path.join('output', 'new-name.pdf'),
            prompt_for_output_path(
                'worksheet.pdf',
                exists_func=lambda path: path == os.path.join('output', 'worksheet.pdf'),
                input_func=lambda _: next(responses),
                print_func=lambda _: None,
            )
        )

    def test_prompt_for_output_path_can_increment_name(self):
        existing_files = {
            os.path.join('output', 'worksheet.pdf'),
            os.path.join('output', 'worksheet-1.pdf'),
        }
        self.assertEqual(
            os.path.join('output', 'worksheet-2.pdf'),
            prompt_for_output_path(
                'worksheet.pdf',
                exists_func=existing_files.__contains__,
                input_func=lambda _: 'i',
                print_func=lambda _: None,
            )
        )

    def test_main_writes_to_output_directory_for_default_filename(self):
        with patch.object(Mg, 'get_list_of_questions', return_value=[]), \
             patch.object(Mg, 'make_question_page'), \
             patch.object(Mg, 'make_answer_page'), \
             patch('run.os.makedirs') as mock_makedirs, \
             patch('run.prompt_for_output_path', return_value=os.path.join('output', 'worksheet.pdf')), \
             patch('run.FPDF.output') as mock_output:
            main('+', 9, 0, 'worksheet.pdf', None)

        mock_makedirs.assert_called_once_with('output', exist_ok=True)
        mock_output.assert_called_once_with(os.path.join('output', 'worksheet.pdf'))

    def test_main_passes_output_size_to_generator(self):
        with patch.object(Mg, 'get_list_of_questions', return_value=[]), \
             patch.object(Mg, 'make_question_page'), \
             patch.object(Mg, 'make_answer_page'), \
             patch('run.os.makedirs'), \
             patch('run.prompt_for_output_path', return_value=os.path.join('output', 'worksheet.pdf')), \
             patch('run.FPDF.output'), \
             patch('run.MathWorksheetGenerator') as mock_generator:
            instance = mock_generator.return_value
            instance.get_list_of_questions.return_value = []
            main('+', 9, 0, 'worksheet.pdf', None, output_size='xlarge')

        mock_generator.assert_called_once_with('+', 9, 0, output_size='xlarge')


if __name__ == '__main__':
    unittest.main()
