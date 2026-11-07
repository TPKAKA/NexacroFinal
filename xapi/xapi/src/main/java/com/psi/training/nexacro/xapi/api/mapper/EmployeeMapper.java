package com.psi.training.nexacro.xapi.api.mapper;

import com.psi.training.nexacro.xapi.entity.entity.EmployeeEntity;
import org.apache.ibatis.annotations.Mapper;

import java.util.List;

@Mapper
public interface EmployeeMapper {
    List<EmployeeEntity> getAll(EmployeeEntity employeeEntity);

    int insert(EmployeeEntity employeeEntity);

    int update(EmployeeEntity employeeEntity);

    int delete(String employeeId);
}
