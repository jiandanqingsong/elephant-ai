# 查询并输出所有人物节点
print("\n所有人物：")  # 输出查询所有人物的提示
people = graph.run("MATCH (n:Person) RETURN n.name AS name")  # 查询所有人物节点的名字
for person in people:  # 遍历查询结果
    print(f"人物: {person['name']}")  # 输出每个人物的名称
# 查询并输出所有人物之间的关系
print("\n所有关系：")  # 输出查询所有关系的提示
relations_query = graph.run("MATCH (n)-[r]->(m) RETURN n.name AS from_name, r, m.name AS to_name")  # 查询所有关系
for relation in relations_query:  # 遍历查询结果
    print(f"从 '{relation['from_name']}' 到 '{relation['to_name']}' 的关系: {relation['r']}")  # 输出每个关系的描述
    # 清空数据库中的所有节点和关系
graph.run("MATCH (n) DETACH DELETE n")  # 删除所有节点及其关系，以便重新开始构建图谱
# 读取CSV文件数据，文件路径为'/mnt/cgshare/triples.csv'
df = pd.read_csv('/mnt/cgshare/triples.csv', encoding='utf-8')  # 读取CSV文件，并将其存储到DataFrame中
# 获取CSV文件中的所有人物（head和tail列中的所有人物）
person_set = set(df['head']).union(set(df['tail']))  # 使用union确保不重复，获取所有不同的人物
for person in person_set:  # 遍历所有人物
    graph.run(f"CREATE (:Person {{name: '{person}'}})")  # 为每个不同的人物创建一个节点
# 遍历CSV文件中的每一行数据，创建人物之间的关系
for _, row in df.iterrows():  # 使用iterrows()遍历每一行数据
    from_person = row['head']  # 获取关系的起始人物（head列）
    to_person = row['tail']  # 获取关系的目标人物（tail列）
    relation_type = row['label']  # 获取人物之间的关系类型（label列）
    # 使用MATCH查询语句查找人物节点，创建它们之间的关系
    graph.run(f"""
		MATCH (from:Person {{name: '{from_person}'}})，(to:Person {{name: '{to_person}'}})
		CREATE (from)-[:{relation_type}]->(to)
	""")  # 创建从'from_person'到'to_person'的关系，关系类型是relation_type
	import pandas as pd  # 导入pandas库，用于读取CSV文件
from py2neo import Graph  # 导入py2neo库，用于操作Neo4j图数据库

# 连接到本地的Neo4j数据库
graph = Graph("bolt://localhost:7687", auth=("neo4j", "pwd123qaz")) # 请替换为你的密码

# 验证连接
print(graph)