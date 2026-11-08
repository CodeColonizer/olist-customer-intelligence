-- Brazilian states with full names and official macro-regions.
-- Small reference table used for regional analysis and the Power BI map.
drop table if exists dim_states;
create table dim_states (
    state_code  text primary key,
    state_name  text not null,
    region      text not null
);

insert into dim_states (state_code, state_name, region) values
    ('AC', 'Acre', 'North'),
    ('AP', 'Amapá', 'North'),
    ('AM', 'Amazonas', 'North'),
    ('PA', 'Pará', 'North'),
    ('RO', 'Rondônia', 'North'),
    ('RR', 'Roraima', 'North'),
    ('TO', 'Tocantins', 'North'),
    ('AL', 'Alagoas', 'Northeast'),
    ('BA', 'Bahia', 'Northeast'),
    ('CE', 'Ceará', 'Northeast'),
    ('MA', 'Maranhão', 'Northeast'),
    ('PB', 'Paraíba', 'Northeast'),
    ('PE', 'Pernambuco', 'Northeast'),
    ('PI', 'Piauí', 'Northeast'),
    ('RN', 'Rio Grande do Norte', 'Northeast'),
    ('SE', 'Sergipe', 'Northeast'),
    ('DF', 'Distrito Federal', 'Centre-West'),
    ('GO', 'Goiás', 'Centre-West'),
    ('MT', 'Mato Grosso', 'Centre-West'),
    ('MS', 'Mato Grosso do Sul', 'Centre-West'),
    ('ES', 'Espírito Santo', 'Southeast'),
    ('MG', 'Minas Gerais', 'Southeast'),
    ('RJ', 'Rio de Janeiro', 'Southeast'),
    ('SP', 'São Paulo', 'Southeast'),
    ('PR', 'Paraná', 'South'),
    ('RS', 'Rio Grande do Sul', 'South'),
    ('SC', 'Santa Catarina', 'South');
