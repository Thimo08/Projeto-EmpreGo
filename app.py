from flask import Flask, render_template, request, redirect, session, send_from_directory
from mysql.connector import Error #biblioteca para bd mysql
from config import * #arquivo config.py
from db_functions import * #funções de banco de dados
import os 
import time

app = Flask(__name__)
app.secret_key = SECRET_KEY
app.config['UPLOAD_FOLDER'] = 'uploads/'

#ROTA DA PÁGINA INICIAL (TODOS ACESAM)
@app.route('/')
def index():
    if session:
        if 'adm' in session:
            login = 'adm'
        else:
            login = 'empresa'
    else:
        login = False

    try:
        comandoSQL = '''
        SELECT vaga.*, empresa.nome_empresa 
        FROM vaga 
        JOIN empresa ON vaga.id_empresa = empresa.id_empresa
        WHERE vaga.status = 'ativa'
        ORDER BY vaga.id_vaga DESC;
        '''
        conexao, cursor = conectar_db()
        cursor.execute(comandoSQL)
        vagas = cursor.fetchall()
        return render_template('index.html', vagas=vagas, login=login)
    except Error as erro:
        return f"ERRO! Erro de Banco de Dados: {erro}"
    except Exception as erro:
        return f"ERRO! Outros erros: {erro}"
    finally:
        encerrar_db(cursor, conexao)

#ROTA PARA PÁGINA DE LOGIN 
@app.route('/login', methods=['GET', 'POST'])
def login():
    if session:
        if 'adm' in session:
            return redirect('/adm')
        else:
            return redirect('/empresa')

    if request.method == 'GET':
        return render_template('login.html')

    if request.method == 'POST':
        email = request.form['email']
        senha = request.form['senha']

        if not email or not senha:  # Corrigi aqui para verificar ambos os campos corretamente
            erro = "Os campos precisam estar preenchidos!"
            return render_template('login.html', msg_erro=erro)

        if email == MASTER_EMAIL and senha == MASTER_PASSWORD:
            session['adm'] = True
            return redirect('/adm')

        try:
            conexao, cursor = conectar_db()
            comandoSQL = 'SELECT * FROM empresa WHERE email = %s AND senha = %s'
            cursor.execute(comandoSQL, (email, senha))
            empresa = cursor.fetchone()

            if not empresa:
                return render_template('login.html', msgerro='E-mail e/ou senha estão errados!')

            # Acessar os dados como dicionário
            if empresa['status'] == 'inativa':
                return render_template('login.html', msgerro='Empresa desativada! Procure o administrador!')

            session['id_empresa'] = empresa['id_empresa']
            session['nome_empresa'] = empresa['nome_empresa']
            return redirect('/empresa')
        
        except Error as erro:
            return f"ERRO! Erro de Banco de Dados: {erro}"
        except Exception as erro:
            return f"ERRO! Outros erros: {erro}"
        finally:
            encerrar_db(cursor, conexao)


 #ROTA DA PÁGINA DO ADMIN
@app.route('/adm')
def adm():
    #Se não houver sessão ativa
    if not session:
        return redirect('/login')
    #Se não for o administrador
    if not 'adm' in session:
        return redirect('/empresa')
  
    try:
        conexao, cursor = conectar_db()
        comandoSQL = 'SELECT * FROM Empresa WHERE status = "ativa"'
        cursor.execute(comandoSQL)
        empresas_ativas = cursor.fetchall()

        comandoSQL = 'SELECT * FROM Empresa WHERE status = "inativa"'
        cursor.execute(comandoSQL)
        empresas_inativas = cursor.fetchall()

        return render_template('adm.html', empresas_ativas=empresas_ativas, empresas_inativas=empresas_inativas)
    except Error as erro:
        return f"ERRO! Erro de Banco de Dados: {erro}"
    except Exception as erro:
        return f"ERRO! Outros erros: {erro}"
    finally:
        encerrar_db(cursor, conexao)
    
#ROTA PARA CADASTRAR NOVA EMPRESA
@app.route('/cadastrar_empresa', methods=['POST','GET'])
def cadastrar_empresa():
    #verificar se tem um sessão
    if not session:
        return redirect('/login')
    
    #se não for ADM
    if not 'adm' in session:
        return redirect('/empresa')
    
    if request.method == 'GET':
        return render_template('cadastrar_empresa.html')
    
    #tratando os dados do form
    if request.method == 'POST':
        nome_empresa = request.form['nome_empresa']
        cnpj = limpar_input(request.form['cnpj'])
        telefone = limpar_input(request.form['telefone'])
        email = request.form['email']
        senha = request.form['senha']

        #Verificar
        if not nome_empresa or not cnpj or not telefone or not email or not senha:
            return render_template('cadastrar_empresa.html', msg_erro="Todos os campos são obrigatórios!")
        
        try:
            conexao, cursor = conectar_db()
            comandoSQL = 'INSERT INTO empresa (nome_empresa, cnpj, telefone, email,senha) VALUES (%s,%s,%s,%s,%s)'
            cursor.execute(comandoSQL, (nome_empresa, cnpj, telefone, email, senha))
            conexao.commit() #envia os dados para o BD
            return redirect('/adm')
        except Error as erro:
            if erro.errno == 1062:
                return render_template('cadastrar_empresa.html', msg_erro="Já existe uma empresa com esse Email!")
            else:
                return f"Erro de BD: {erro}"
        except Exception as erro:
            return f"Erro de BackEnd: {erro}"
        finally:
            encerrar_db(cursor, conexao)

#ROTA PARA EDITAR EMPRESA 
@app.route('/editar_empresa/<int:id_empresa>', methods=['GET','POST'])
def editar_empresa(id_empresa):
    if not session:
        return redirect('/login')
    
    if not session['adm']:
        return redirect('/login')
    
    if request.method == 'GET':
        try:
            conexao, cursor = conectar_db()
            comandoSQL = 'SELECT * FROM empresa WHERE id_empresa = %s'
            cursor.execute(comandoSQL, (id_empresa,))
            empresa = cursor.fetchone()
            return render_template('editar_empresa.html', empresa=empresa)
        except Error as erro:
            return f"Erro de BD: {erro}"
        except Exception as erro:
            return f"Erro de BackEnd: {erro}"
        finally:
            encerrar_db(cursor, conexao)

            #tratando os dados do form
    if request.method == 'POST':
        nome_empresa = request.form['nome_empresa']
        cnpj = limpar_input(request.form['cnpj'])
        telefone = limpar_input(request.form['telefone'])
        email = request.form['email']
        senha = request.form['senha']

        #Verificar
        if not nome_empresa or not cnpj or not telefone or not email or not senha:
            return render_template('editar_empresa.html', msg_erro="Todos os campossão obrigatórios!")
        
        try:
            conexao, cursor = conectar_db()
            comandoSQL = '''
            UPDATE empresa 
            SET nome_empresa = %s, cnpj = %s, telefone = %s, email = %s, senha = %s WHERE id_empresa = %s;
            '''
            cursor.execute(comandoSQL, (nome_empresa, cnpj, telefone, email, senha, id_empresa))
            conexao.commit() #envia os dados para o BD
            return redirect('/adm')
        except Error as erro:
            if erro.errno == 1062:
                return render_template('editar_empresa.html', msg_erro="Já existe uma empresa com esse Email!")
            else:
                return f"Erro de BD: {erro}"
        except Exception as erro:
            return f"Erro de BackEnd: {erro}"
        finally:
            encerrar_db(cursor, conexao)

#ROTA PARA ATIVAR OU INATIVAR EMPRESA 
@app.route('/status_empresa/<int:id_empresa>')
def status_empresa(id_empresa):
    if not session:
        return redirect('/login')
    if not session['adm']:
        return redirect('/login')

    try:
        conexao, cursor = conectar_db()
        comandoSQL = 'SELECT status FROM empresa WHERE id_empresa = %s'
        cursor.execute(comandoSQL, (id_empresa,))
        status_empresa = cursor.fetchone()
        if status_empresa['status'] == 'ativa':
            novo_status = 'inativa'
        else:
            novo_status = 'ativa'

        comandoSQL = 'UPDATE empresa SET status = %s WHERE id_empresa = %s'
        cursor.execute(comandoSQL, (novo_status, id_empresa))
        conexao.commit()
        #se a empresa estiver sendo desativada, as vagas tambeém serão
        if novo_status == 'inativa':
            comandoSQL = 'UPDATE vaga SET status = %s WHERE id_empresa = %s'
            cursor.execute(comandoSQL, (novo_status, id_empresa))
            conexao.commit()
        return redirect('/adm')
    except Error as erro:
        return f"Erro de BD: {erro}"
    except Exception as erro:
        return f"Erro de BackEnd: {erro}"
    finally:
        encerrar_db(cursor, conexao)

#ROTA PARA EXCLUIR A EMPRESA
@app.route('/excluir_empresa/<int:id_empresa>')
def excluir_empresa(id_empresa):
    #validar sessão
    if not session:
        return redirect('/login')
    if not session ['adm']:
        return redirect('/login')
    
    try:
        conexao, cursor = conectar_db()
        comandoSQL = '''SELECT curriculo FROM candidato
        WHERE id_vaga IN (
        SELECT id_vaga
        FROM vaga
        WHERE id_empresa = %s
        );
        '''
        cursor.execute(comandoSQL, (id_empresa,))
        curriculos = cursor.fetchall()
        for curriculo in curriculos:
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], curriculo['curriculo']))
        conexao.commit()

        #EXCLUIR AS VAGAS RELACIONADAS NA EMPRESA EXCLUIDA
        comandoSQL = '''DELETE FROM candidato
        WHERE id_vaga IN (
        SELECT id_vaga
        FROM vaga
        WHERE id_empresa = %s
        );
        '''
        cursor.execute(comandoSQL, (id_empresa,))
        conexao.commit()


        #EXCLUIR AS VAGAS RELACIONADAS NA EMPRESA EXCLUIDA
        comandoSQL = 'DELETE FROM vaga WHERE id_empresa = %s'
        cursor.execute(comandoSQL, (id_empresa,))
        conexao.commit()

    #EXCLUIR CADASTRO DA EMPRESA
        comandoSQL = 'DELETE FROM empresa WHERE id_empresa = %s'
        cursor.execute(comandoSQL, (id_empresa,))
        conexao.commit()
        return redirect('/adm')
    except Error as erro:
            return f"Erro de BD: {erro}"
    except Exception as erro:
            return f"Erro de BackEnd: {erro}"
    finally:
        encerrar_db(cursor, conexao)

#ROTA DA PÁGINA DE GESTÃO DAS EMPRESAS
@app.route('/empresa')
def empresa():
    #Verifica se não tem sessão ativa
    if not session:
        return redirect('/login')
    #Verifica se o adm está tentando acessar indevidamente
    if 'adm' in session:
        return redirect('/adm')

    id_empresa = session['id_empresa']
    nome_empresa = session['nome_empresa']

    try:
        conexao, cursor = conectar_db()
        comandoSQL = 'SELECT * FROM vaga WHERE id_empresa = %s AND status = "ativa" ORDER BY id_vaga DESC'
        cursor.execute(comandoSQL, (id_empresa,))
        vagas_ativas = cursor.fetchall()

        comandoSQL = 'SELECT * FROM vaga WHERE id_empresa = %s AND status = "inativa" ORDER BY id_vaga DESC'
        cursor.execute(comandoSQL, (id_empresa,))
        vagas_inativas = cursor.fetchall()

        return render_template('empresa.html', nome_empresa=nome_empresa, vagas_ativas=vagas_ativas, vagas_inativas=vagas_inativas)         
    except Error as erro:
        return f"ERRO! Erro de Banco de Dados: {erro}"
    except Exception as erro:
        return f"ERRO! Outros erros: {erro}"
    finally:
        encerrar_db(cursor, conexao)



@app.route('/cadastrar_vaga', methods=['POST','GET'])
def cadastrar_vaga():
    #Verifica se não tem sessão ativa
    if not session:
        return redirect('/login')
    #Verifica se o adm está tentando acessar indevidamente
    if 'adm' in session:
        return redirect('/adm')
    
    if request.method == 'GET':
        return render_template('cadastrar_vaga.html')
    
    if request.method == 'POST':
        titulo = request.form['titulo']
        descricao = request.form['descricao']
        formato = request.form['formato']
        tipo = request.form['tipo']
        local = ''
        local = request.form['local']
        salario = ''
        salario = limpar_input(request.form['salario'])
        id_empresa = session['id_empresa']

        if not titulo or not descricao or not formato or not tipo:
            return render_template('cadastrar_vaga.html', msg_erro="Os campos obrigatório precisam estar preenchidos!")
        
        try:
            conexao, cursor = conectar_db()
            comandoSQL = '''
            INSERT INTO Vaga (titulo, descricao, formato, tipo, local, salario, id_empresa)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            '''
            cursor.execute(comandoSQL, (titulo, descricao, formato, tipo, local, salario, id_empresa))
            conexao.commit()
            return redirect('/empresa')
        except Error as erro:
            return f"ERRO! Erro de Banco de Dados: {erro}"
        except Exception as erro:
            return f"ERRO! Outros erros: {erro}"
        finally:
            encerrar_db(cursor, conexao)



@app.route('/editar_vaga/<int:id_vaga>', methods=['GET','POST'])
def editarvaga(id_vaga):
    #Verifica se não tem sessão ativa
    if not session:
        return redirect('/login')
    #Verifica se o adm está tentando acessar indevidamente
    if 'adm' in session:
        return redirect('/adm')

    if request.method == 'GET':
        try:
            conexao, cursor = conectar_db()
            comandoSQL = 'SELECT * FROM vaga WHERE id_vaga = %s;'
            cursor.execute(comandoSQL, (id_vaga,))
            vaga = cursor.fetchone()
            return render_template('editar_vaga.html', vaga=vaga)
        except Error as erro:
            return f"ERRO! Erro de Banco de Dados: {erro}"
        except Exception as erro:
            return f"ERRO! Outros erros: {erro}"
        finally:
            encerrar_db(cursor, conexao)

    if request.method == 'POST':
        titulo = request.form['titulo']
        descricao = request.form['descricao']
        formato = request.form['formato']
        tipo = request.form['tipo']
        local = request.form['local']
        salario = limpar_input(request.form['salario'])

        if not titulo or not descricao or not formato or not tipo:
            return redirect('/empresa')
        
        try:
            conexao, cursor = conectar_db()
            comandoSQL = '''
            UPDATE vaga SET titulo=%s, descricao=%s, formato=%s, tipo=%s, local=%s, salario=%s
            WHERE id_vaga = %s;
            '''
            cursor.execute(comandoSQL, (titulo, descricao, formato, tipo, local, salario, id_vaga))
            conexao.commit()
            return redirect('/empresa')
        except Error as erro:
            return f"ERRO! Erro de Banco de Dados: {erro}"
        except Exception as erro:
            return f"ERRO! Outros erros: {erro}"
        finally:
            encerrar_db(cursor, conexao)


#ROTA PARA ALTERAR O STATUS DA VAGA
@app.route("/status_vaga/<int:id_vaga>")
def statusvaga(id_vaga):
    #Verifica se não tem sessão ativa
    if not session:
        return redirect('/login')
    #Verifica se o adm está tentando acessar indevidamente
    if 'adm' in session:
        return redirect('/adm')

    try:
        conexao, cursor = conectar_db()
        comandoSQL = 'SELECT status FROM vaga WHERE id_vaga = %s;'
        cursor.execute(comandoSQL, (id_vaga,))
        vaga = cursor.fetchone()
        if vaga['status'] == 'ativa':
            status = 'inativa'
        else:
            status = 'ativa'

        comandoSQL = 'UPDATE vaga SET status = %s WHERE id_vaga = %s'
        cursor.execute(comandoSQL, (status, id_vaga))
        conexao.commit()
        return redirect('/empresa')
    except Error as erro:
        return f"ERRO! Erro de Banco de Dados: {erro}"
    except Exception as erro:
        return f"ERRO! Outros erros: {erro}"
    finally:
        encerrar_db(cursor, conexao)



#ROTA PARA EXCLUIR VAGA
@app.route("/excluir_vaga/<int:id_vaga>")
def excluir_vaga(id_vaga):
    #Verifica se não tem sessão ativa
    if not session:
        return redirect('/login')
    #Verifica se o adm está tentando acessar indevidamente
    if 'adm' in session:
        return redirect('/adm')

    try:
        conexao, cursor = conectar_db()

        # Primeiro, obter todos os currículos associados a esta vaga
        comandoSQL = 'SELECT curriculo FROM candidato WHERE id_vaga = %s'
        cursor.execute(comandoSQL, (id_vaga,))
        curriculos = cursor.fetchall()

        # Excluir os arquivos
        for curriculo in curriculos:
            nome_arquivo = curriculo['curriculo']
            if nome_arquivo:
                try:
                    os.remove(os.path.join(app.config['UPLOAD_FOLDER'], nome_arquivo))
                except OSError as e:
                    print(f"Erro ao remover arquivo: {e}")



        #EXCLUIR AS VAGAS RELACIONADAS NA EMPRESA EXCLUIDA
        comandoSQL = 'DELETE FROM candidato WHERE id_vaga = %s'
        cursor.execute(comandoSQL, (id_vaga,))
        conexao.commit()

        comandoSQL = 'DELETE FROM vaga WHERE id_vaga = %s AND status = "inativa"'
        cursor.execute(comandoSQL, (id_vaga,))
        conexao.commit()
        return redirect('/empresa')
    except Error as erro:
        return f"ERRO! Erro de Banco de Dados: {erro}"
    except Exception as erro:
        return f"ERRO! Outros erros: {erro}"
    finally:
        encerrar_db(cursor, conexao)


#ROTA PARA VER DETALHES DA VAGA
@app.route('/sobre_vaga/<int:id_vaga>')
def sobre_vaga(id_vaga):
    try:
        comandoSQL = '''
        SELECT vaga.*, empresa.nome_empresa 
        FROM vaga 
        JOIN empresa ON vaga.id_empresa = empresa.id_empresa 
        WHERE vaga.id_vaga = %s;
        '''
        conexao, cursor = conectar_db()
        cursor.execute(comandoSQL, (id_vaga,))
        vaga = cursor.fetchone()
        
        if not vaga:
            return redirect('/')
        
        return render_template('sobre_vaga.html', vaga=vaga)
    except Error as erro:
        return f"ERRO! Erro de Banco de Dados: {erro}"
    except Exception as erro:
        return f"ERRO! Outros erros: {erro}"
    finally:
        encerrar_db(cursor, conexao)     


@app.route('/cadastrar_candidato/<int:id_vaga>', methods=['POST', 'GET'])
def cadastrar_candidato(id_vaga):
    # Verifica se não tem sessão ativa
    if 'empresa' in session:
        return redirect('/')

    if 'adm' in session:
        return redirect('/')

    if request.method == 'GET':
        return render_template('cadastrar_candidato.html',id_vaga=id_vaga)

    if request.method == 'POST':
        nome = request.form['nome']
        telefone = request.form['telefone']
        email = request.form['email']
        curriculo = request.files['file']
        

        if not nome or not telefone or not email or not curriculo.filename:
            return render_template('cadastrar_candidato.html', msg_erro="Os campos obrigatórios precisam estar preenchidos!")

        try:
            timestamp = int(time.time())  # cod
            nome_curriculo = f'{timestamp}_{id_vaga}_{curriculo.filename}'
            curriculo.save(os.path.join(app.config['UPLOAD_FOLDER'], nome_curriculo))
            conexao, cursor = conectar_db()
            comandoSQL = '''
            INSERT INTO Candidato (nome, telefone, email, curriculo, id_vaga)
            VALUES (%s, %s, %s, %s, %s)
            '''
            cursor.execute(comandoSQL, (nome, telefone, email, nome_curriculo, id_vaga))
            conexao.commit()
                # Limpa o currículo da sessão após o uso
            return render_template('retorno.html', feedback=True)

        except Error as erro:
            print(f"ERRO! Erro de Banco de Dados: {erro}")
            return render_template('retorno.html', feedback=False)
        except Exception as erro:
            print(f"ERRO! Outros erros: {erro}")
            return render_template('retorno.html', feedback=False)
        finally:
            encerrar_db(cursor, conexao)



@app.route('/ver_candidato/<int:id_vaga>')
def ver_candidato(id_vaga):
    # Verifica se não tem sessão ativa
    if not session:
        return redirect('/login')
    # Verifica se o adm está tentando acessar indevidamente
    if 'adm' in session:
        return redirect('/adm')

    try:
        conexao, cursor = conectar_db()
        comandoSQL = '''
        SELECT * FROM Candidato WHERE id_vaga = %s;
        '''
        cursor.execute(comandoSQL, (id_vaga,))
        candidato = cursor.fetchall()
        
        return render_template('ver_candidato.html', candidato=candidato)
    except Error as erro:
        return f"ERRO! Erro de Banco de Dados: {erro}"
    except Exception as erro:
        return f"ERRO! Outros erros: {erro}"
    finally:
        encerrar_db(cursor, conexao)


@app.route('/download/<filename>')
def download(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

@app.route("/excluir_candidato/<int:id_candidato>")
def excluir_candidato(id_candidato):
    # Verifica se não tem sessão ativa
    if not session:
        return redirect('/login')
    # Verifica se o adm está tentando acessar indevidamente
    if 'adm' in session:
        return redirect('/adm')

    try:
        conexao, cursor = conectar_db()
        
        # Primeiro, obtenha o id_vaga do candidato
        comandoSQL = 'SELECT id_vaga, curriculo FROM candidato WHERE id_candidato = %s'
        cursor.execute(comandoSQL, (id_candidato,))
        resultado = cursor.fetchone()
        
        if not resultado:
            return "Candidato não encontrado", 404

        id_vaga, nome_arquivo = resultado['id_vaga'], resultado['curriculo']

        # Tenta remover o arquivo do currículo
        if nome_arquivo:
            try:
                os.remove(os.path.join(app.config['UPLOAD_FOLDER'], nome_arquivo))
            except OSError as e:
                print(f"Erro ao remover arquivo: {e}")

        # Exclui o candidato do banco de dados
        comandoSQL = 'DELETE FROM candidato WHERE id_candidato = %s'
        cursor.execute(comandoSQL, (id_candidato,))
        conexao.commit()

        # Redireciona para a página de visualização de candidatos da vaga específica
        return redirect(f'/ver_candidato/{id_vaga}')
    
    except Error as erro:
        print(f"Erro de Banco de Dados: {erro}")
        return f"ERRO! Erro de Banco de Dados: {erro}"
    except Exception as erro:
        print(f"Outro erro: {erro}")
        return f"ERRO! Outros erros: {str(erro)}"
    finally:
        encerrar_db(cursor, conexao)




    #ROTA PARA TRATAR O ERRO 404 - PÁGINA NÃO ENCONTRADA


@app.route('/pesquisar_vagas', methods=['GET'])
def pesquisar_vagas():

    # Obtém o termo de pesquisa enviado como parâmetro na URL
    termo = request.args.get('termo')
    if not termo:
        return "Por favor, forneça um termo para pesquisa.", 400

    try:
        conexao, cursor = conectar_db()
        comandoSQL = '''
        SELECT vaga.id_vaga,vaga.titulo, vaga.descricao, vaga.formato, vaga.tipo, vaga.local, vaga.salario, empresa.nome_empresa
        FROM vaga
        JOIN empresa ON vaga.id_empresa = empresa.id_empresa
        WHERE (vaga.titulo LIKE %s OR empresa.nome_empresa LIKE %s OR vaga.tipo LIKE %s OR vaga.formato LIKE %s) AND vaga.status = "ativa";
        '''
        termo_pesquisa = f"{termo}%"
        cursor.execute(comandoSQL, (termo_pesquisa, termo_pesquisa, termo_pesquisa, termo_pesquisa))
        vagas = cursor.fetchall()

        return render_template('pesquisar_vagas.html', vagas=vagas, termo=termo)
    except Error as erro:
        return f"ERRO! Erro de Banco de Dados: {erro}"
    except Exception as erro:   
        return f"ERRO! Outros erros: {erro}"
    finally:
        encerrar_db(cursor, conexao)


@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

#ROTA PARA LOGOUT (ENCERRA AS SESSÕES)
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

#FINAL DO CÓDIGO
if __name__=='__main__':
    app.run(debug=True)

