import os
from django.test import TestCase
from django.utils import timezone
from dateutil.relativedelta import relativedelta
from core.models import Usuario, Turma, Matricula, RespostaExProgramacao, ExercicioDeProgramacao, Prova, InteracaoUsarioExercicio, ExercicioProgramado
from core.choices import Resultado
from core.date_utils import *
from .factories import *

CUR_DIR = os.path.abspath(os.path.dirname(__file__))


class UsuarioTestCase(TestCase):
    def setUp(self):
        self.aluno = cria_aluno(1)
        self.aluno_liberado = cria_aluno(2)
        self.turma = cria_turma_atual()
        self.matricula_aluno = cria_matricula(self.aluno, self.turma)
        self.matricula_aluno_liberado = cria_matricula(self.aluno_liberado,
                                                       self.turma, True)

    def test_turmas_atuais_liberadas(self):
        self.assertEqual(0, len(self.aluno.turmas_atuais_liberadas()))
        self.assertEqual(1, len(self.aluno_liberado.turmas_atuais_liberadas()))


class TurmaTestCase(TestCase):
    def test_alunos_matriculados(self):
        anos = sorted(list(range(-1, 2)) * 2)
        inicios = [tz_delta(months=-2, years=y) for y in anos]
        fins = [tz_delta(months=+2, years=y) for y in anos]
        turmas = [
            cria_turma(nome='turma{0}'.format(i), inicio=inicio, fim=fim)
            for i, (inicio, fim) in enumerate(zip(inicios, fins))
        ]
        # Metade dos alunos vem da turma anterior
        turma2aluno = {}
        alunos_por_turma = 2
        metade_turma = alunos_por_turma // 2
        alunos = [cria_aluno(i) for i in range(metade_turma)]
        for turma in turmas:
            n = len(alunos)
            for i in range(n, n + metade_turma):
                alunos.append(cria_aluno(i))
            for aluno in alunos[-alunos_por_turma:]:
                cria_matricula(aluno=aluno, turma=turma)
                turma2aluno.setdefault(turma, []).append(aluno)

        todos_alunos = set(alunos)
        for turma in turmas:
            matriculados = set(turma2aluno[turma])
            nao_matriculados = todos_alunos - matriculados
            for aluno in matriculados:
                self.assertTrue(turma.esta_matriculado(aluno))
            for aluno in nao_matriculados:
                self.assertFalse(turma.esta_matriculado(aluno))

    def cria_varias_turmas(self):
        # Datas
        self.ano_passado = tz_delta(years=-1)
        self.dois_meses_atras = tz_delta(months=-2)
        self.mes_passado = tz_delta(months=-1)
        self.ontem = tz_ontem()
        self.hoje = tz_agora()
        self.amanha = tz_amanha()
        self.ano_que_vem = tz_delta(years=1)
        # Alunos
        self.aluno1 = cria_aluno(1)
        self.aluno2 = cria_aluno(2)
        # Turmas
        self.turma1 = cria_turma(inicio=self.dois_meses_atras, fim=self.ontem)
        self.turma2 = cria_turma(inicio=self.ano_passado, fim=self.ano_que_vem)
        self.turma3 = cria_turma(inicio=self.mes_passado, fim=self.amanha)
        self.turma4 = cria_turma()
        # Matricula
        cria_matricula(self.aluno1, self.turma1)
        cria_matricula(self.aluno1, self.turma3)
        cria_matricula(self.aluno1, self.turma4)
        cria_matricula(self.aluno2, self.turma1)
        cria_matricula(self.aluno2, self.turma2)

    def test_date_range(self):
        self.cria_varias_turmas()

        date_range1 = Turma.objects.get_date_range(self.aluno1)
        date_range2 = Turma.objects.get_date_range(self.aluno2)
        self.assertEqual(self.mes_passado.date(), date_range1.start_date)
        self.assertEqual(self.ano_passado.date(), date_range2.start_date)
        self.assertEqual(self.hoje.date(), date_range1.end_date)
        self.assertEqual(self.hoje.date(), date_range2.end_date)

    def test_lista_turmas_do_aluno(self):
        self.cria_varias_turmas()

        turmas1 = Turma.objects.do_aluno(self.aluno1)
        self.assertEqual(3, len(turmas1))
        self.assertTrue(self.turma1 in turmas1)
        self.assertTrue(self.turma3 in turmas1)
        self.assertTrue(self.turma4 in turmas1)
        turmas2 = Turma.objects.do_aluno(self.aluno2)
        self.assertEqual(2, len(turmas2))
        self.assertTrue(self.turma1 in turmas2)
        self.assertTrue(self.turma2 in turmas2)
        turmas_atuais1 = Turma.objects.atuais().do_aluno(self.aluno1)
        self.assertEqual(2, len(turmas_atuais1))
        self.assertTrue(self.turma3 in turmas_atuais1)
        self.assertTrue(self.turma4 in turmas_atuais1)
        turmas_atuais2 = Turma.objects.do_aluno(self.aluno2).atuais()
        self.assertEqual(1, len(turmas_atuais2))
        self.assertTrue(self.turma2 in turmas_atuais2)


class ExercicioDeProgramacaoTestCase(TestCase):
    def test_lista_publicados(self):
        publicado = cria_exercicio()
        nao_publicado = cria_exercicio(
            titulo='Hello World 2',
            descricao='Escreva outro programa que imprime "Olá, Raimundo!"',
            publicado=False)
        exercicios_publicados = ExercicioDeProgramacao.objects.publicados()
        self.assertTrue(publicado in exercicios_publicados)
        self.assertTrue(nao_publicado not in exercicios_publicados)


class RespostaExProgramacaoTestCase(TestCase):
    def setUp(self):
        self.usuario = cria_aluno(1)
        self.arquivo_teste = cria_arquivo_teste()
        self.exercicio = cria_exercicio()
        self.sucesso = cria_resposta(autor=self.usuario,
                                     exercicio=self.exercicio)
        self.falha = cria_resposta(autor=self.usuario,
                                   exercicio=self.exercicio,
                                   resultado=Resultado.ERRO)

    def test_sucesso_ou_falha(self):
        self.assertTrue(self.sucesso.sucesso)
        self.assertFalse(self.falha.sucesso)

    def test_lista_de_falhas(self):
        self.falha.lista_de_falhas = []
        self.assertEqual(['Sem erros.'], self.falha.lista_de_falhas)

        falhas = ['Erro1', 'Erro2', 'Erro3']
        self.falha.lista_de_falhas = falhas
        self.assertEqual(falhas, self.falha.lista_de_falhas)

    def test_stack_traces(self):
        self.falha.stack_traces = []
        self.assertEqual(['-'], self.falha.stack_traces)

        stack_traces = ['StackTrace1', 'StackTrace2', 'StackTrace3']
        self.falha.stack_traces = stack_traces
        self.assertEqual(stack_traces, self.falha.stack_traces)

    def test_nao_inclui_deletados(self):
        deletado = cria_resposta(autor=self.usuario,
                                 exercicio=self.exercicio,
                                 resultado=Resultado.ERRO,
                                 deletado=True)
        respostas = RespostaExProgramacao.objects.all()
        self.assertTrue(self.sucesso in respostas)
        self.assertTrue(self.falha in respostas)
        self.assertTrue(deletado not in respostas)

    def test_lista_somente_do_autor(self):
        outro_aluno = cria_aluno(10)
        resposta_outro_aluno = cria_resposta(autor=outro_aluno,
                                             exercicio=self.exercicio,
                                             resultado=Resultado.OK)
        respostas = RespostaExProgramacao.objects.por(self.usuario).all()
        self.assertTrue(self.sucesso in respostas)
        self.assertTrue(self.falha in respostas)
        self.assertTrue(resposta_outro_aluno not in respostas)

    def test_conta_exercicios_por_dia(self):
        aluno = cria_aluno(10)
        amanha = tz_amanha()
        dias = 3
        comeco = tz_delta(days=-2 * (dias - 1))
        exercicios = [cria_exercicio() for _ in range(dias)]
        for i in range(dias):
            for j in range(i + 1):
                resposta = cria_resposta(autor=aluno,
                                         exercicio=exercicios[j],
                                         resultado=Resultado.OK,
                                         data_submissao=tz_delta(days=-2 * i))
        # Todos
        epd = RespostaExProgramacao.objects.por(
            aluno).conta_exercicios_por_dia()
        for d, c in zip(DateRange(comeco, amanha), [3, 0, 2, 0, 1]):
            self.assertEqual(c, epd[d.date()])
        # Últimos
        inicio = (comeco + inc_dia()).date()
        epd = RespostaExProgramacao.objects.por(
            aluno).conta_exercicios_por_dia(inicio=inicio)
        for d, c in zip(DateRange(comeco, amanha), [0, 0, 2, 0, 1]):
            self.assertEqual(c, epd[d.date()])
        # Primeiros
        fim = tz_ontem().date()
        epd = RespostaExProgramacao.objects.por(
            aluno).conta_exercicios_por_dia(fim=fim)
        for d, c in zip(DateRange(comeco, amanha), [3, 0, 2, 0, 0]):
            self.assertEqual(c, epd[d.date()])
        # Meio
        epd = RespostaExProgramacao.objects.por(
            aluno).conta_exercicios_por_dia(inicio=inicio, fim=fim)
        for d, c in zip(DateRange(comeco, amanha), [0, 0, 2, 0, 0]):
            self.assertEqual(c, epd[d.date()])

    # TODO A partir da função RespostaExProgramacaoManager.ultima_submissao não tem testes


class ExercicioProgramadoTestCase(TestCase):
    def setUp(self):
        self.usuario_staff = cria_staff()
        self.aluno = cria_aluno(1)
        self.aluno_liberado = cria_aluno(2)
        self.turma = cria_turma_atual()
        self.matricula_staff = cria_matricula(self.usuario_staff, self.turma)
        self.matricula_aluno = cria_matricula(self.aluno, self.turma)
        self.matricula_aluno_liberado = cria_matricula(self.aluno_liberado,
                                                       self.turma, True)
        self.exercicio_atual = cria_exercicio_programado_atual(
            cria_exercicio(), self.turma)
        self.exercicio_passado = cria_exercicio_programado_passado(
            cria_exercicio(), self.turma)
        self.exercicio_futuro = cria_exercicio_programado_futuro(
            cria_exercicio(), self.turma)
        self.exercicio_prova_futura = cria_exercicio()
        self.exercicio_prova_atual = cria_exercicio()
        self.prova_atual = cria_prova_atual(
            self.turma, exercicios=[self.exercicio_prova_atual])
        self.prova_futura = cria_prova_futura(
            self.turma, exercicios=[self.exercicio_prova_futura])

    def test_lista_todos_para_staff(self):
        exercicios_programados_disponiveis = ExercicioProgramado.objects.disponiveis_para(
            self.usuario_staff)
        exercicios_disponiveis_ids = [
            e.id for e in self.usuario_staff.exercicios_disponiveis()
        ]
        self.assertTrue(
            self.exercicio_atual in exercicios_programados_disponiveis)
        self.assertTrue(
            self.exercicio_passado in exercicios_programados_disponiveis)
        self.assertTrue(
            self.exercicio_futuro in exercicios_programados_disponiveis)
        self.assertTrue(
            self.exercicio_atual.exercicio.id in exercicios_disponiveis_ids)
        self.assertTrue(
            self.exercicio_passado.exercicio.id in exercicios_disponiveis_ids)
        self.assertTrue(
            self.exercicio_futuro.exercicio.id in exercicios_disponiveis_ids)
        self.assertTrue(
            self.exercicio_prova_futura.id in exercicios_disponiveis_ids)
        self.assertTrue(
            self.exercicio_prova_atual.id in exercicios_disponiveis_ids)

    def test_lista_todos_para_aluno(self):
        exercicios_disponiveis = ExercicioProgramado.objects.disponiveis_para(
            self.aluno)
        exercicios_disponiveis_ids = [
            e.id for e in self.aluno.exercicios_disponiveis()
        ]
        self.assertTrue(self.exercicio_atual in exercicios_disponiveis)
        self.assertFalse(self.exercicio_passado in exercicios_disponiveis)
        self.assertFalse(self.exercicio_futuro in exercicios_disponiveis)
        self.assertTrue(
            self.exercicio_atual.exercicio.id in exercicios_disponiveis_ids)
        self.assertFalse(
            self.exercicio_passado.exercicio.id in exercicios_disponiveis_ids)
        self.assertFalse(
            self.exercicio_futuro.exercicio.id in exercicios_disponiveis_ids)
        self.assertFalse(
            self.exercicio_prova_futura.id in exercicios_disponiveis_ids)
        self.assertTrue(
            self.exercicio_prova_atual.id in exercicios_disponiveis_ids)

    def test_lista_todos_para_aluno_liberado(self):
        exercicios_disponiveis = ExercicioProgramado.objects.disponiveis_para(
            self.aluno_liberado)
        exercicios_disponiveis_ids = [
            e.id for e in self.aluno_liberado.exercicios_disponiveis()
        ]
        self.assertTrue(self.exercicio_atual in exercicios_disponiveis)
        self.assertFalse(self.exercicio_passado in exercicios_disponiveis)
        self.assertTrue(self.exercicio_futuro in exercicios_disponiveis)
        self.assertTrue(
            self.exercicio_atual.exercicio.id in exercicios_disponiveis_ids)
        self.assertFalse(
            self.exercicio_passado.exercicio.id in exercicios_disponiveis_ids)
        self.assertTrue(
            self.exercicio_futuro.exercicio.id in exercicios_disponiveis_ids)
        self.assertFalse(
            self.exercicio_prova_futura.id in exercicios_disponiveis_ids)
        self.assertTrue(
            self.exercicio_prova_atual.id in exercicios_disponiveis_ids)


class ProvaTestCase(TestCase):
    def test_disponivel_para(self):
        aluno_matriculado = cria_aluno(1)
        aluno_nao_matriculado = cria_aluno(2)

        inicio_turma = tz_delta(months=-2)
        fim_turma = tz_delta(months=+2)
        inicio_prova_atual = tz_delta(hours=-1)
        fim_prova_atual = tz_delta(hours=+1)
        inicio_prova_passada = tz_delta(hours=-1, months=-1)
        fim_prova_passada = tz_delta(hours=+1, months=-1)

        turma = cria_turma(nome='turma1', inicio=inicio_turma, fim=fim_turma)
        cria_matricula(aluno=aluno_matriculado, turma=turma)
        prova_passada = Prova.objects.create(inicio=inicio_prova_passada,
                                             fim=fim_prova_passada,
                                             titulo='Prova 1',
                                             turma=turma)
        prova_atual = Prova.objects.create(inicio=inicio_prova_atual,
                                           fim=fim_prova_atual,
                                           titulo='Prova 2',
                                           turma=turma)

        self.assertFalse(prova_passada.disponivel_para(aluno_matriculado))
        self.assertFalse(prova_passada.disponivel_para(aluno_nao_matriculado))
        self.assertTrue(prova_atual.disponivel_para(aluno_matriculado))
        self.assertFalse(prova_atual.disponivel_para(aluno_nao_matriculado))

        # Provas do aluno matriculado
        provas = Prova.objects.disponiveis_para(aluno_matriculado)
        self.assertTrue(prova_atual in provas)
        self.assertTrue(prova_passada not in provas)
        provas = aluno_matriculado.provas_disponiveis()
        self.assertTrue(prova_atual in provas)
        self.assertTrue(prova_passada not in provas)
        # Provas do aluno não matriculado
        provas = Prova.objects.disponiveis_para(aluno_nao_matriculado)
        self.assertTrue(prova_atual not in provas)
        self.assertTrue(prova_passada not in provas)
        provas = aluno_nao_matriculado.provas_disponiveis()
        self.assertTrue(prova_atual not in provas)
        self.assertTrue(prova_passada not in provas)

    def test_fica_disponivel_por_mais_tempo_para_aluno_que_precisa(self):
        aluno_regular = cria_aluno(1)
        aluno_mais_tempo = cria_aluno(2)

        inicio_turma = tz_delta(months=-2)
        fim_turma = tz_delta(months=+2)
        inicio_prova_regular = tz_delta(hours=-2)
        fim_prova_regular = tz_delta(hours=-1)
        inicio_prova_mais_tempo = tz_delta(hours=-2)
        fim_prova_mais_tempo = tz_delta(hours=+1)

        turma_regular = cria_turma(nome='turma regular',
                                   inicio=inicio_turma,
                                   fim=fim_turma)
        turma_mais_tempo = cria_turma(nome='turma mais tempo',
                                      inicio=inicio_turma,
                                      fim=fim_turma)
        cria_matricula(aluno=aluno_regular, turma=turma_regular)
        cria_matricula(aluno=aluno_mais_tempo, turma=turma_regular)
        cria_matricula(aluno=aluno_mais_tempo, turma=turma_mais_tempo)
        prova_regular = Prova.objects.create(inicio=inicio_prova_regular,
                                             fim=fim_prova_regular,
                                             titulo='Prova regular',
                                             turma=turma_regular)
        prova_mais_tempo = Prova.objects.create(inicio=inicio_prova_mais_tempo,
                                                fim=fim_prova_mais_tempo,
                                                titulo='Prova mais tempo',
                                                turma=turma_mais_tempo)

        self.assertFalse(prova_regular.disponivel_para(aluno_regular))
        self.assertFalse(prova_regular.disponivel_para(aluno_mais_tempo))
        self.assertTrue(prova_mais_tempo.disponivel_para(aluno_mais_tempo))
        self.assertFalse(prova_mais_tempo.disponivel_para(aluno_regular))

        # Provas do aluno regular
        provas = Prova.objects.disponiveis_para(aluno_regular)
        self.assertTrue(prova_regular not in provas)
        self.assertTrue(prova_mais_tempo not in provas)
        provas = aluno_regular.provas_disponiveis()
        self.assertTrue(prova_regular not in provas)
        self.assertTrue(prova_mais_tempo not in provas)
        # Provas do aluno não matriculado
        provas = Prova.objects.disponiveis_para(aluno_mais_tempo)
        self.assertTrue(prova_regular not in provas)
        self.assertTrue(prova_mais_tempo in provas)
        provas = aluno_mais_tempo.provas_disponiveis()
        self.assertTrue(prova_regular not in provas)
        self.assertTrue(prova_mais_tempo in provas)


class InteracaoUsarioExercicioTestCase(TestCase):
    def test_atualiza_interacao_com_exercicio(self):
        exercicio = ExercicioDeProgramacao.objects.create()
        autor = cria_aluno(1)
        # Primeira tentativa
        ex = RespostaExProgramacao.objects.create(exercicio=exercicio,
                                                  autor=autor,
                                                  resultado=Resultado.ERRO)
        interacao = InteracaoUsarioExercicio.objects.get(usuario=autor,
                                                         exercicio=exercicio)
        self.assertEqual(1, interacao.tentativas)
        self.assertEqual(Resultado.ERRO, interacao.melhor_resultado)

        # Segunda tentativa
        ex = RespostaExProgramacao.objects.create(exercicio=exercicio,
                                                  autor=autor,
                                                  resultado=Resultado.ERRO)
        interacao = InteracaoUsarioExercicio.objects.get(usuario=autor,
                                                         exercicio=exercicio)
        self.assertEqual(2, interacao.tentativas)
        self.assertEqual(Resultado.ERRO, interacao.melhor_resultado)

        # Atualizando resposta
        ex.resultado = Resultado.OK
        ex.save()
        interacao = InteracaoUsarioExercicio.objects.get(usuario=autor,
                                                         exercicio=exercicio)
        self.assertEqual(2, interacao.tentativas)
        self.assertEqual(Resultado.OK, interacao.melhor_resultado)
