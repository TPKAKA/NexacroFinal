package com.psi.training.nexacro.xapi.api.controller;

import com.nexacro.java.xapi.data.DataSet;
import com.nexacro.java.xapi.tx.PlatformException;
import com.psi.training.nexacro.xapi.api.service.EmployeeService;
import com.psi.training.nexacro.xapi.common.NexacroConvert;
import com.psi.training.nexacro.xapi.entity.entity.EmployeeEntity;
import com.psi.training.nexacro.xapi.entity.response.ColumnEntity;
import com.psi.training.nexacro.xapi.entity.response.Dataset;
import com.psi.training.nexacro.xapi.entity.response.ResponseEntity;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import jakarta.servlet.http.HttpServletRequest;


import java.io.IOException;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

@Controller
@RequestMapping("employee")
public class EmployeeController {
    @Autowired
    private EmployeeService employeeService;

    @RequestMapping("")
    public String getAll(HttpServletRequest request, Model model) throws IOException, PlatformException {
        List<Map<String, String>> employees = new ArrayList<>();
        employees = employeeService.getAll(null);

        System.out.println(employees.size());

        List<ColumnEntity> columns = NexacroConvert.convertEntityToColumn(new EmployeeEntity());
        List<Dataset> datasets = new ArrayList<>();
        Dataset dataset = new Dataset();
        dataset.setColumns(columns);
        dataset.setRows(employees);
        dataset.setId("IDDataset");

        datasets.add(dataset);
        ResponseEntity entity = new ResponseEntity(0, "fail", datasets);
        model.addAttribute("data", entity);

        return "nexacroView";
    }

    @PostMapping("/search")
    public String search (HttpServletRequest request, Model model) throws IOException, PlatformException {

        DataSet dataSet = NexacroConvert.getRequestData(request,"dsInput");
        List<Map<String, String>> employees = new ArrayList<>();
        List<Map<String, String>> requestBody = NexacroConvert.convertDatasetToListMap(dataSet);

        if (requestBody.size() != 0) {
            employees = employeeService.getAll(requestBody.get(0));
        } else {
            employees = employeeService.getAll(null);
        }

        List<ColumnEntity> columns = NexacroConvert.convertEntityToColumn(new EmployeeEntity());

        List<Dataset> datasets = new ArrayList<>();
        Dataset dataset = new Dataset();
        dataset.setColumns(columns);
        dataset.setRows(employees);
        dataset.setId("IDDataset");

        datasets.add(dataset);
        ResponseEntity entity = new ResponseEntity(0, "SUCCESS", datasets);
        model.addAttribute("data", entity);

        return "nexacroView";
    }

    @PostMapping("/save")
    public String save(HttpServletRequest request, Model model) {
        DataSet dataSet = NexacroConvert.getRequestData(request, "dsEmployee");
        ResponseEntity entity;

        try {
            employeeService.save(dataSet);
            entity = new ResponseEntity(0, "SUCCESS", new ArrayList<>());
        } catch (Exception e) {
            entity = new ResponseEntity(-1, e.getMessage(), new ArrayList<>());
        }
        model.addAttribute("data", entity);

        return "nexacroView";
    }

}
