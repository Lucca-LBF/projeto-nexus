from django.shortcuts import render
import plotly.graph_objects as go
import plotly.io as pio

CHAVE_SESSAO = 'simulacao'


def dashboard(request):
    simulacao = request.session.get(CHAVE_SESSAO)

    tempo_dias = simulacao.get('tempo_amostra', 30)

    total_sem_iot = simulacao.get('total_sem_iot', 0)
    total_com_iot = simulacao.get('total_com_iot', 0)
    economia = simulacao.get('resultado_liquido', 0)

    percentual_economia = (
        economia / total_sem_iot * 100
        if total_sem_iot > 0 else 0
    )

    dados_dias = simulacao.get('dados_grafico_dias', [])
    y_sem_iot = simulacao.get('dados_grafico_sem_iot', [])
    y_com_iot = simulacao.get('dados_grafico_com_iot', [])

   
    if tempo_dias <= 30:
        eixo_x = [f'Dia {d}' for d in dados_dias]
        unidade = 'Diária'
    else:
        num_meses = (tempo_dias + 29) // 30
        eixo_x = [f'Mês {i}' for i in range(1, num_meses + 1)]
        unidade = 'Mensal'

        if y_sem_iot and y_com_iot:
            y_sem_iot = [
                sum(y_sem_iot[i * 30:(i + 1) * 30])
                for i in range(num_meses)
            ]
            y_com_iot = [
                sum(y_com_iot[i * 30:(i + 1) * 30])
                for i in range(num_meses)
            ]

    grafico = go.Figure()

    grafico.add_trace(go.Scatter(
        x=eixo_x,
        y=y_sem_iot,
        mode='lines+markers',
        name='Operação Sem IoT (Corretiva)',
        line=dict(color='#dc2626', width=3),
    ))

    grafico.add_trace(go.Scatter(
        x=eixo_x,
        y=y_com_iot,
        mode='lines+markers',
        name='Operação Com IoT (Preditiva)',
        line=dict(color='#16a34a', width=3),
    ))

    grafico.update_layout(
        title=f'Projeção {unidade} dos Custos de Falha',
        xaxis_title='Período de Análise',
        yaxis_title='Custo de Falhas (R$)',
        template='plotly_white',
        hovermode='x unified',
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=1.02,
            xanchor='right',
            x=1,
        ),
    )

    grafico_html = pio.to_html(
        grafico,
        full_html=False,
        config={'responsive': True},
    )

    contexto = {
        'total_sem_iot': round(total_sem_iot, 2),
        'total_com_iot': round(total_com_iot, 2),
        'economia': round(economia, 2),
        'percentual_economia': round(percentual_economia, 2),
        'grafico_linhas': grafico_html,
        'nota_explicativa': ('O gráfico apresenta os custos operacionais ao longo do período simulado.'),
    }

    return render(request, 'dashboard/index.html', contexto)