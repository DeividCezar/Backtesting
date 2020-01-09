# 1. Importando bibliotecas necessárias:
# Necessita-se a instação das bibliotecas: altair, vega, DateTime e pandas-datareader.

import pandas as pd
import pandas_datareader as pdr
from datetime import datetime
import altair as alt
alt.renderers.enable('notebook')


# 2. Importação de dados da Petrobras usado para exemplo de recorte da base:

base_petrobras = pdr.DataReader('PETR4.SA', 'yahoo', '2019-1-1', '2019-1-31').reset_index()


# 3. Gráfico que ilutra médias móveis:

def sma(ativo, start, end):
    # São três entradas: o nome do ativo que deve ser seguido de ".SA", a data inicial e a data final.
    
    # Importando dados sobre o ativo:
    atv = pdr.DataReader(ativo, 'yahoo', start, end).reset_index()

    # Criando as médias móveis de curto e longo prazo (média do preço das últimas 21 e 72 aberturas) para o ativo:
    atv['SMA21'] = atv.Open.rolling(21).mean()
    atv['SMA72'] = atv.Open.rolling(72).mean()
    
    # Agrupando, apenas as colunas do preço de abertura ("open") e as médias móveis, em três colunas: 
    atv = atv[['Date','Open','SMA21','SMA72']].melt('Date', var_name='Indice', value_name='Valor (R$)')
    
    # Ocultando o número de casas decimais da coluna valor:
    atv['Valor (R$)'] = round(atv['Valor (R$)'], 2)
      
    # Construção do gráfico do preço de ativo e das médias móveis:
    
    # Recurso visual para tirar a cor das outras linhas quando o mouse sobrepor a curva:
    highlight = alt.selection(type='single', on='mouseover', fields=['Indice'], nearest=True, empty="all")

    plt_inds = alt.Chart(atv).mark_line().encode(
        x = 'Date:T',
        y = 'Valor (R$):Q',
        color = alt.condition(highlight, alt.Color('Indice:N'), alt.value('rgb(200,200,200)')),
        tooltip = ['Date', 'Valor (R$)']
    ).add_selection(
        highlight
    ).properties(
        width = 830,
        height = 300,
        title = 'Preço de abertura e médias móveis de ' + ativo[0:-3]
        # Observe que retiramos ".SA" do nome do ativo no título.
    )

    # Resultado da função - gráfico de preço e médias:
    return(plt_inds)


# 4. Função que retorna negociações:

def strategy(lt, start, end):
    # Diferente da primeira entrada da função anterior, essa deve ser uma lista de ativos. No demais, seguem as datas de início e fim.

    # Criando data frame para anexar os resultados da estratégia para cada ativo:
    neg = pd.DataFrame()
        
    # Aplicando estratégia para cada ativo da lista:    
    for i in lt:
    
        # Importando dados sobre os ativos:
        atv = pdr.DataReader(i, 'yahoo', start, end).reset_index()

        # Criando as médias móveis de curto e longo prazo:
        atv['SMA21'] = atv.Open.rolling(21).mean()
        atv['SMA72'] = atv.Open.rolling(72).mean()

        # Criando listas para anexar negociações:
        entry = []
        exit = []

        # Filtrando compras e vendas:
        for j in range(1, atv.shape[0]):
            
            # Se a média móvel de curto prazo ultrapassar a de longo prazo é hora de comprar:
            if atv.loc[j, 'SMA21'] >= atv.loc[j, 'SMA72'] and atv.loc[j-1, 'SMA21'] < atv.loc[j-1, 'SMA72']:
                entry.append(atv.loc[j])
            
            # Se a média móvel de longo prazo ultrapassar a de curto prazo é hora de vender:
            elif atv.loc[j, 'SMA21'] <= atv.loc[j, 'SMA72'] and atv.loc[j-1, 'SMA21'] > atv.loc[j-1, 'SMA72'] and entry != []:
                exit.append(atv.loc[j])
                
                # Note que é importante garantir que alguma compra tenha sido feita para poder vender.
                # Por isso deve-se verificar se "entry" não está vazio.

        # Convertendo listas criadas com as compras e vendas em Dataframes, apenas, com as colunas 'Date' e 'Open':
        neg_entry = pd.DataFrame(entry).reset_index(drop = True)[['Date','Open']]
        neg_exit = pd.DataFrame(exit).reset_index(drop = True)[['Date','Open']]

        # Concatenando e eliminando possíveis linhas com 'Na' (caso a última compra ainda não tenha sido vendida):
        neg_i = pd.concat([neg_entry, neg_exit], axis=1).dropna(axis=0, how='any')
        
        # Adicionando o nome do ativo nas linhas e removendo '.SA' necessário para importanção dos dados do ativo no Yahoo:
        neg_i['Ativo'] = i[0:-3]
        
        # Concatenando com as negociações dos outros ativos:
        neg = neg.append(neg_i)
    
    # Renomeando colunas:
    neg.columns = ['Data da compra', 'Preço de entrada', 'Data da venda', 'Preço de saída', 'Ativo']
    
    # Organizando indexes para adição de novas colunas, caso não fosse feito, daria erro de múltiplos indexes no 'for' seguinte:
    neg = neg.reset_index(drop=True)
    
    # Adicionando novas colunas:
    for k in range(0, neg.shape[0]):
        
        # Rentabilidade:
        neg.at[k, 'Variação (%)'] = round((neg.loc[k, 'Preço de saída'] / neg.loc[k, 'Preço de entrada'] - 1)* 100, 2)
            
        # Duração da trade:
        start = datetime.strptime(str(neg.loc[k, 'Data da compra']), '%Y-%m-%d %H:%M:%S')
        end = datetime.strptime(str(neg.loc[k, 'Data da venda']), '%Y-%m-%d %H:%M:%S')
        neg.at[k, 'Duração (dias)'] = (end - start).days
        
    # Ordenando pela data da compra e reorganizando indexes:
    neg = neg.sort_values(by='Data da compra').reset_index(drop=True)
    
    # Resultado da função - data frame com negociações:
    return (neg)


# 5. Scatter plot das negociações

def scatter(lt, start, end):
    # As entradas são semelhantes a função anterior.
    
    # Utilizaremos o data frame gerado pela função que retorna as negociações:
    df = strategy(lt, start, end)
    
    # Construção do gráfico da duração e variação das negociações:
    
    plot_rent_dur = alt.Chart(df).mark_circle(size=60).encode(
        x = 'Duração (dias):Q',
        y = 'Variação (%):Q',
        color = 'Ativo:N',
        tooltip = ['Duração (dias)', 'Variação (%)']
    ).properties(
        title = 'Comparativo entre variação e rentabilidade das negociações'
    )
    
    # Resultado da função - scatter plot:
    return(plot_rent_dur)


# 6. Comparação entre adotar a estratégia e realizar um investimento único:

def inv_un(lt, start, end):
    # Entradas já vistas.
    
    # Utilizaremos o data frame gerado pela função que retorna as negociações:
    df = strategy(lt, start, end)
    
    # Inicialmente, agrupa-se o data frame pelos ativos - somando os preços de compra e de venda:
    df_2 = df.groupby('Ativo').sum()

    # Em seguida, calcula-se a variação entre valor investido e o valor de venda:
    df_2['Estratégia do backtesting'] = round((df_2['Preço de saída'] / df_2['Preço de entrada'] - 1) * 100, 2)

    # A única coluna que nos interessa é a criada anteriormente:
    df_2 = df_2[['Estratégia do backtesting']].reset_index()

    # Agora vamos verificar como seria a variação dos investimentos caso fossem realizados uma única vez.
    # Ou seja, depois da primeira vez comprado, só seria vendido na última data de venda no quadro de negociações.

    # Criando lista para anexar resultados:
    lt = []

    # Calculando a variação para cada ativo negociado:
    for i in list(df_2.Ativo):

        # Selecionando apenas as linhas do data frame inicial que contém o ativo "i" (um ativo de cada vez):
        data = df.loc[df['Ativo'] == i]

        # Calculando variação:
        x = round((list(data['Preço de saída'])[-1] / list(data['Preço de entrada'])[0] - 1) * 100, 2)

        # Anexando na lista:
        lt.append(x)

    # Juntando ambos os tipos de variação (investimento único e estratégia):
    df_2 = pd.concat([df_2, pd.DataFrame(lt)], axis=1)

    # Renomeando coluna da variação do investimento único:
    df_2 = df_2.rename({0:'Investimento único'}, axis=1)
    
    # Agrupando dados em três colunas para plotagem:
    df_2 = df_2.melt('Ativo', var_name='Tipo de investimento', value_name='Variação (%)')
    
    # Transforma o resultado obtido em um gráfico:
    plot = alt.Chart(df_2).mark_bar().encode(
        x = 'Variação (%):Q',
        y = alt.Y('Tipo de investimento:N', title=None),
        color = 'Tipo de investimento:N',
        row = 'Ativo:N',
        tooltip=['Variação (%)']
    ).properties(
        width = 610
    # Optamos por não colocar título nesse gráfico pois o Vega 2 está com problemas para plotar o texto do título centralizado. 
    )
    
    # Retorna o gráfico contruído:
    return(plot)